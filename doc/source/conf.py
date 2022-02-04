# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
#  nova documentation build configuration file
#
# Refer to the Sphinx documentation for advice on configuring this file:
#
#   http://www.sphinx-doc.org/en/stable/config.html

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../../'))

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autodoc',     # the autodoc extensions uses files generated by apidoc
#    'sphinx.ext.autosummary',
    'sphinx_copybutton',
    'sphinxcontrib.openapi',
]

#autosummary_generate = True  # Make _autosummary files and include them

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

todo_include_todos = True

source_parsers = {
    # '.md': 'recommonmark.parser.CommonMarkParser'
}

# The suffix of source filenames.
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = "motley_cue"
copyright = "2021-present, Diana Gudu"
author = "Diana Gudu"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
# release = version.release_string
# The short X.Y version.
# version = version.version_string

# A list of glob-style patterns that should be excluded when looking for
# source files. They are matched against the source file names relative to the
# source directory, using slashes as directory separators on all platforms.
exclude_patterns = []

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['motley_cue.']

# -- Options for man page output ----------------------------------------------

# If true, show URL addresses after external links.
#man_show_urls = False

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'alabaster'

# Set link name generated in the top bar.
html_title = 'motley_cue'

html_show_sourcelink = True

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'description': 'SSH client wrapper for SSH with OIDC access token',
    'logo': 'logos/motley-cue.png',
    'github_user': 'dianagudu',
    'github_repo': 'motley_cue',
    'canonical_url': 'https://dianagudu.github.io/motley_cue/',
    'touch_icon': 'logos/motley-cue-notext.png',
    'show_relbar_bottom': True,
    'show_relbar_top': False,
    'show_powered_by': False,
    'fixed_sidebar': True,
    # colors
    #'sidebar_text': '#005792f7',
    'gray_1': '#005792f7', # dark -> blue
    'gray_2': '#eef1f3ff', # light -> gray
    'gray_3': '#005792f7', # medium -> blue
    'note_bg': '#005792f7', # blue
    'pre_bg': '#eef1f3ff', # light
    'link': '#005792f7', # blue
    'link_hover': '#fd5f00ff', # orange
    'sidebar_header': '#fd5f00ff', # orange
    'sidebar_list': '#fd5f00ff', # orange
    'narrow_sidebar_bg': '#005792f7', # Background of sidebar when narrow window forces it to the bottom of the page.
    'narrow_sidebar_fg': '#ffffff', # Text color of same.
    'narrow_sidebar_link': '#ffffff', #Link color of same.
    'note_bg': '#e6f0f7ff',
    'note_border': '#e6f0f7ff',
    'warn_bg': '#fcece3ff',
    'warn_border': '#fcece3ff',
    # fonts
    'head_font_family': 'Barlow Semi Condensed Medium, sans-serif',
    'caption_font_family': 'Barlow Semi Condensed, sans-serif',
    # 'code_font_family': 'Liberation Mono, Roboto Mono, monospace',
    'font_family': 'Barlow Semi Condensed, sans-serif',
    # 'font_size': 'medium',
    'code_font_size': 'small',
    # 'caption_font_size': 'medium',
}

## sphinx-copybutton configs
copybutton_prompt_text = "$ "
copybutton_only_copy_prompt_lines = True
copybutton_remove_prompts = True
copybutton_copy_empty_lines = False
copybutton_line_continuation_character = "\\"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [
    '_static',
    '_static/logos/motley-cue.ico'
]

#html_logo = '_static/logos/motley-cue-white.png'

html_favicon = '_static/logos/motley-cue.ico'

# Add any paths that contain "extra" files, such as .htaccess or
# robots.txt.
# html_extra_path = ['_extra']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%Y-%m-%d %H:%M'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = False


# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index': ['about.html', 'navigation.html', 'relations.html', 
        'sourcelink.html', 'searchbox.html' ],
}

html_css_files = [
    'css/fonts.css',
    'css/custom.css',
]

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'hu', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'ru', 'sv', 'tr'
#html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# Now only 'ja' uses this config value
#html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = 'doc-out'

# -- Options for LaTeX output -------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index', 'motley_cue.tex', u'Documentation',
     author, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = "_static/logos/motley-cue.png"

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True

# enable member doc strings
# https://stackoverflow.com/questions/56693832/should-sphinx-be-able-to-document-instance-attributes-in-a-class
autodoc_default_options = {
    'members':         True,
    'member-order':    'bysource',
}
