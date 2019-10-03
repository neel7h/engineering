plugin = () ->

  codeHighlighter =
    id: 'codeHighlighter'
    Facade:
      codeHighlighter:
        processLanguages:($selector)->
          $selector.find('pre code').each((i, item)->
            hljs.highlightBlock(item)
          )

  codeHighlighter

# AMD support (use in require)
if define?.amd?
  define(['highlight'], () ->
    return plugin()
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.codeHighlighter = plugin()
else if module?.exports?
  module.exports = plugin()
