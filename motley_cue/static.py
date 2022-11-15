"""Helper module for serving static files."""
import markdown


TEMPLATE = """<!DOCTYPE html>
<html>
    <head>
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1, minimal-ui">
		<title>{{title}}</title>
		<style>
			body {
				box-sizing: border-box;
				min-width: 200px;
				max-width: 980px;
				margin: 0 auto;
				padding: 45px;
			}

			@media (prefers-color-scheme: dark) {
				body {
					background-color: #0d1117;
				}
			}
		</style>
	</head>
<body>
<div class="markdown-body">
{{content}}
</div>
</body>
</html>
"""


def md_to_html(mdfile: str, title: str = "Title") -> str:
    """Convert a markdown file to HTML."""
    with open(mdfile, "r", encoding="utf-8") as input_file:
        md = input_file.read()

    extensions = ["extra", "smarty", "codehilite", "toc", "sane_lists"]
    html = markdown.markdown(md, extensions=extensions, output_format="html")
    doc = TEMPLATE.replace("{{content}}", html).replace("{{title}}", title)
    return doc
