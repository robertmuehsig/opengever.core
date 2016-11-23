from collections import OrderedDict
from five import grok
from jsonschema import Draft4Validator
from opengever.base.schemadump.config import GEVER_SQL_TYPES
from opengever.base.schemadump.config import GEVER_TYPES
from opengever.base.schemadump.config import JSON_SCHEMA_FIELD_TYPES
from opengever.base.schemadump.field import FieldDumper
from opengever.base.schemadump.field import SQLFieldDumper
from opengever.base.schemadump.helpers import DirectoryHelperMixin
from opengever.base.schemadump.helpers import translate_de
from opengever.base.schemadump.log import setup_logging
from opengever.base.utils import pretty_json
from opengever.core.debughelpers import get_first_plone_site
from opengever.core.debughelpers import setup_plone
from os.path import join as pjoin
from plone import api
from plone.dexterity.utils import iterSchemataForType
from plone.supermodel.interfaces import FIELDSETS_KEY
from Products.CMFPlone.interfaces import IPloneSiteRoot
from sqlalchemy.ext.declarative.base import _is_mapped_class
from zope.dottedname.resolve import resolve as resolve_dotted
from zope.schema import getFieldsInOrder
import transaction


log = setup_logging(__name__)


class SchemaDumper(object):
    """Dumps a simple Python representation of a zope.schema Schema interface.
    """

    def dump(self, schema):
        log.info("  Dumping schema %r" % schema.__identifier__)

        fields = []
        field_dumper = FieldDumper(schema)

        for name, field in getFieldsInOrder(schema):
            field_dump = field_dumper.dump(field)
            fields.append(field_dump)

        schema_dump = OrderedDict((
            ('name', schema.__identifier__),
            ('fields', fields),
        ))

        # Fieldsets
        fieldsets = self._get_fieldsets_for_schema(schema)
        if fieldsets:
            schema_dump['fieldsets'] = fieldsets

        return schema_dump

    def _get_fieldsets_for_schema(self, schema):
        fieldsets_for_schema = {}

        # Should probably use plone.autoform.utils.mergedTaggedValuesForIRO
        # fpr this instead, to merge tagged values across interfaces
        for fs in schema.queryTaggedValue(FIELDSETS_KEY, []):
            fieldsets_for_schema[fs.label] = fs.fields
        return fieldsets_for_schema


class SQLSchemaDumper(object):
    """Dumps a simple Python representation of a SQLAlchemy mapped class.
    """

    def dump(self, klass):
        log.info("  Dumping SQL schema %r" % klass.__name__)

        fields = []
        field_dumper = SQLFieldDumper(klass)

        tbl = klass.__table__
        for column in tbl.columns:
            if column.foreign_keys:
                # XXX: Skip ForeignKeys for now, because it's unclear how
                # exactly they should be handled.
                continue
            field_dump = field_dumper.dump(column)
            fields.append(field_dump)

        schema_dump = OrderedDict((
            ('name', klass.__name__),
            ('fields', fields),
        ))

        return schema_dump


class TypeDumper(object):
    """Dumps a simple Python representation of an FTI and its schemas.
    """

    def dump(self, portal_type):
            log.info("Dumping schemas for portal_type %r" % portal_type)
            fti = self._get_fti(portal_type)
            type_title = translate_de(fti.title, domain=fti.i18n_domain)

            schemas = []
            schema_dumper = SchemaDumper()

            for schema in iterSchemataForType(portal_type):
                schema_dump = schema_dumper.dump(schema)
                schemas.append(schema_dump)

            type_dump = OrderedDict((
                ('portal_type', portal_type),
                ('title', type_title),
                ('schemas', schemas),
            ))

            return type_dump

    def _get_fti(self, portal_type):
        types_tool = api.portal.get_tool('portal_types')
        return types_tool[portal_type]


class SQLTypeDumper(object):
    """Dumps a simple Python representation of SQLAlchemy mapped type.
    """

    def dump(self, sql_type):
            log.info("Dumping schemas for SQL type%r" % sql_type)
            # SQL type names are prefixed with an underscore to distinguish
            # them from actual portal_types
            dottedname = sql_type.lstrip('_')
            main_klass = resolve_dotted(dottedname)

            schemas = []
            schema_dumper = SQLSchemaDumper()

            # Also consider columns from base classes (inheritance).
            # We only consider one level of inheritance though, we don't look
            # up base classes recursively.
            bases = list(filter(_is_mapped_class, main_klass.__bases__))
            mapper_args = getattr(main_klass, '__mapper_args__', {})

            if bases and 'polymorphic_identity' not in mapper_args:
                raise NotImplementedError(
                    "Unexpected inheritance for %r: Mapped base classes, but "
                    "no polymorphic_identity found!" % main_klass)

            for base_class in bases:
                if list(filter(_is_mapped_class, base_class.__bases__)) != []:
                    raise NotImplementedError(
                        "More than one level of inheritance currently not"
                        "supported when dumping SQL schemas.")

            for cls in [main_klass] + bases:
                schema = schema_dumper.dump(cls)
                schemas.append(schema)

            type_dump = OrderedDict((
                ('portal_type', sql_type),
                ('title', main_klass.__name__),
                ('schemas', schemas),
            ))

            return type_dump


class JSONSchemaGenerator(object):
    """Generates a JSON Schema representation of a single GEVER type (as a
    Python data structure).
    """

    def generate_schema(self, portal_type):
        schema = OrderedDict([
            (u'$schema', u'http://json-schema.org/draft-04/schema#'),
            (u'type', u'object'),
            (u'title', None),
            ('additionalProperties', False),
            (u'properties', {}),
        ])

        if portal_type in GEVER_TYPES:
            type_dumper = TypeDumper()
        elif portal_type in GEVER_SQL_TYPES:
            type_dumper = SQLTypeDumper()
        else:
            raise Exception("Unmapped type: %r" % portal_type)

        type_dump = type_dumper.dump(portal_type)
        type_schema = self._js_type_from_type_dump(type_dump)
        schema.update(type_schema)

        Draft4Validator.check_schema(schema)
        return schema

    def _js_type_from_type_dump(self, type_dump):
        json_schema_type = OrderedDict([
            ('type', 'object'),
            ('properties', {}),
            ('title', type_dump['title']),
        ])

        constraints = {'required': [], 'anyOf': []}

        field_order = []
        # Collect field info from all schemas (base schema + behaviors)
        for schema in type_dump['schemas']:
            # Note: This is not the final / "correct" field order as displayed
            # in the user interface (which should eventually honor fieldsets
            # and plone.autoform directives).
            # The intent here is rather to keep a *consistent* order for now.
            field_order.extend([field['name'] for field in schema['fields']])
            for field in schema['fields']:
                name = field['name']
                json_schema_field = self._js_property_from_field_dump(field)

                if 'default' in field:
                    json_schema_field['default'] = field['default']

                if field.get('vocabulary'):
                    vocab = field['vocabulary']
                    if isinstance(vocab, basestring) and vocab.startswith('<'):
                        json_schema_field['_vocabulary'] = vocab
                    else:
                        json_schema_field['enum'] = vocab

                json_schema_type['properties'][name] = json_schema_field

                if field.get('required', False):
                    constraints['required'].append(name)

                if name in ('title_de', 'title_fr'):
                    constraints['anyOf'].append({'required': [name]})

        for c_name, c_value in constraints.items():
            if c_value:
                json_schema_type[c_name] = c_value

        json_schema_type['field_order'] = field_order
        return json_schema_type

    def _js_property_from_field_dump(self, field):
        """Create a JSON Schema property definition from a field info dump.
        """
        js_property = OrderedDict(title=None, type=None)

        try:
            type_ = JSON_SCHEMA_FIELD_TYPES[field['type']].copy()
            js_property.update(sorted(type_.items()))
        except KeyError:
            raise Exception(
                "Don't know what JS type to map %r to. Please map it in "
                "JSON_SCHEMA_FIELD_TYPES first." % field['type'])

        if field['type'] == 'Choice':
            js_property['type'] = field['value_type']

        js_property['title'] = field['title']
        js_property['description'] = field['description']
        js_property['_zope_schema_type'] = field['type']

        return js_property


class JSONSchemaDumpWriter(DirectoryHelperMixin):
    """Collects JSON Schema representations of common GEVER types and dumps
    them to the file system.
    """

    def dump(self):
        generator = JSONSchemaGenerator()

        for portal_type in GEVER_TYPES + GEVER_SQL_TYPES:
            schema = generator.generate_schema(portal_type)
            filename = '%s.schema.json' % portal_type
            dump_path = pjoin(self.schema_dumps_dir, filename)

            with open(dump_path, 'w') as dump_file:
                json_dump = pretty_json(schema)
                dump_file.write(json_dump)

            log.info('Dumped: %s\n' % dump_path)


def dump_schemas():
    """Dump JSON Schemas of common GEVER content types to the filesystem.

    Dumps will be JSON Schema representations of the schemas and their fields.
    """
    transaction.doom()
    writer = JSONSchemaDumpWriter()
    result = writer.dump()
    return result


class DumpSchemasView(grok.View):
    """Helper view to dump schemas from a running instance.
    """

    grok.name('dump-schemas')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')

    def render(self):
        result = dump_schemas()
        return result


def dump_schemas_zopectl_handler(app, args):
    """Handler for the 'bin/instance dump_schemas' zopectl command.
    """
    setup_plone(get_first_plone_site(app))
    dump_schemas()
