from ftw.testbrowser import browser
from opengever.testing import IntegrationTestCase

html = """
<!DOCTYPE html>
<html>
<head>
<title>Page Title</title>
</head>
<body>

<h1>My First Heading</h1>
<p>My first paragraph.</p>

</body>
</html>
"""


class TestFoo(IntegrationTestCase):
    """Test the base behavior with the help of businesscase dossier.
    """

    def test_using_browser(self):
        browser.open_html(html)
