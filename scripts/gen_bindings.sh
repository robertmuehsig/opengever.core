bin/pyxbgen \
--module-prefix=bindings \
--binding-root=. \
--schema-root=./schemas \
-u ablieferung.xsd -m ablieferung \
-u archivischeNotiz.xsd -m archivischeNotiz \
-u archivischerVorgang.xsd -m archivischerVorgang \
-u arelda.xsd -m arelda \
-u base.xsd -m base \
-u datei.xsd -m datei \
-u dokument.xsd -m dokument \
-u dossier.xsd -m dossier \
-u ordner.xsd -m ordner \
-u ordnungssystem.xsd -m ordnungssystem \
-u ordnungssystemposition.xsd -m ordnungssystemposition \
-u paket.xsd -m paket \
-u provenienz.xsd -m provenienz \
-u zusatzDaten.xsd -m zusatzDaten
