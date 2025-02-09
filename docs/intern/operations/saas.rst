SaaS Deployments
================

SaaS Policies für Release vorbereiten
-------------------------------------

Das package . _opengever-deployments: https://github.com/4teamwork/opengever-deployments/
steht dabei zur Verfügung.

- Meta-package auschecken: ``git clone https://github.com/4teamwork/opengever-deployments``
- mit alle SaaS-policies nach `saas_dev_packages` auschecken: ``dev/checkout.py``
- neue gever version in ``versions.cfg`` aller policies einsetzen, commit message: ``Bump policy to 20xx.y.z release.``. Dies kann auch mit dem ``dev/bump_version.sh`` gemacht werden.
- mit ``dev/for_all_saas_policies`` können commands für alle ausgecheckten policies ausgeführt werden


opengever-deployments Repository aktualisieren
----------------------------------------------

Im Moment sind die SaaS Deployments auf ``ipet.4teamwork.ch`` und ``sia.4teamwork.ch`` installiert.
Skripte und Metadaten für die SaaS-Deployments/Policies werden im Moment im
`opengever-deployments <https://github.com/4teamwork/opengever-deployments>`_
Repository auf github gepflegt. Dieses ist auf dem Server
``ipet.4teamwork.ch`` und ``sia.4teamwork.ch``  nach ``/apps/opengever-deployments`` ausgecheckt und
muss manuell mittels ``git pull`` aktualisiert werden.


Operationen über alle SaaS Deployments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Im `opengever-deployments <https://github.com/4teamwork/opengever-deployments>`_
Repository wird ein JSON-File aller SaaS-Policies/Deployments gepflegt. Die
Liste der Deployments muss dort aktuell gehalten werden. Die Skripte

.. code-block:: bash

    for_all_saas_deployments
    for_all_saas_deployments_parallel

lesen diese Liste aus und wenden einen Bash-Command auf alle darin
aufgeführten Deployments auf dem aktuellem Server (``sia.4teamwork.ch`` oder ``ipet.4teamwork.ch``) im Ordner
``/apps`` an.

Nachfolgend ein Beispiel wie man einen Command für alle SaaS-Deployments
ausführen kann:

.. code-block:: bash

    for_all_saas_deployments "git status"


Deployments aktualisieren
-------------------------

Die Aktualisierung wird normalerweise in zwei Schritten durchgeführt:

- Im ersten Schritt werden nur die unbedingt notwendige upgrade steps durchgeführt (mit ``--skip-deferrable`` flag). Diese sind normalerweise schnell durch und das Deployment ist dann in einem funktionellem Zustand auf der neuen Version.

- Im zweiten Schritt werden noch die restlichen upgrade steps durchgeführt, diese dauern oft viel länger. In diesem Fall ist die ``--force`` flag notwendig, weil es keine Änderungen am Code mehr gibt, aber das Update trotzdem durchgeführt werden sollte.


Einzelnes Deployment aktualisieren
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zur Aktualisierung eines Deployments steht das Skript

.. code-block:: bash

    update_deployment

zur Verfügung. Es muss im buildout-directory des Deployments ausgeführt
werden. Das Skript reported auch in den Slack Channel `gever-notifications
<https://4teamwork.slack.com/archives/gever-notifications>`_.

Nachfolgend ein Beispiel wie ein Dev-Deployment aktualisiert werden kann:

.. code-block:: bash

    cd /apps/01-demo.onegovgever.ch/
    update_deployment --skip-deferrable
    update_deployment --force


Alle SaaS Deployments aktualisieren
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    for_all_saas_deployments[_parallel] "update_deployment --skip-deferrable"
    for_all_saas_deployments[_parallel] "update_deployment --force"


Checkliste für die Aktualisierung
---------------------------------

Vorbereitung Release-Einspielung
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- `SaaS Policies für Release vorbereiten`_
- Wenn nötig:
    - Bumblebee updaten
    - Portal updaten
    - Solr updaten
    - Sitzungsapp updaten
- Auf Kibana_ die Grösse der Deployments überprüfen und sicher stellen dass:
    - Das kleinste Deployment auf jedem Server sich als erster Eintrag im json File (``saas-ipet.json`` und ``saas-sia.json``) befindet (parallele Updates finden nur statt sobald das Update des ersten Deployments fertig ist)
    - Sicherstellen, dass die `solr` memory Einstellungen in den buildout Dateien vernünftig sind (``Xmx512m`` für kleine Deployments, ``Xmx1024m`` für Deployments mit mehr als 10k Dokumente, und ``Xmx2048m`` für noch grössere), z.b.:

    .. code-block:: bash

        [solr]
        vm-opts = -Xms512m -Xmx2048m -Xss256

- Die erwartete Downtime dem Betrieb ankündigen.

.. _Kibana: https://geverreport.4teamwork.ch

Vor der Release-Einspielung
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Immer in einem screen arbeiten: ``screen -S screen_name``
- Cron-Jobs deaktivieren
- Packen deaktivieren

Release-Einspielung
~~~~~~~~~~~~~~~~~~~

- ``opengever-deployments`` updaten
- Deployments updaten:

    .. code-block:: bash

        for_all_saas_deployments_parallel "update_deployment --skip-deferrable"
        for_all_saas_deployments_parallel "update_deployment --force"

Nach der Release-Einspielung
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Wenn nötig:
    - neue :ref:`CronJobs` einrichten
- Packen wieder aktivieren
- Cron-Jobs aktivieren
