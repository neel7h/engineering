# FIXME wtf? what is it and what is it used for ? should we remove it or is it used ? 
plugin = (simplePlaceholder) ->
  simplePlaceholder =
    id: 'simplePlaceholder'

  simplePlaceholder

# AMD support (use in require)
if define?.amd?
  define(['simplePlaceholder'], (simplePlaceholder) ->
    return plugin(simplePlaceholder)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.simplePlaceholder = plugin(simplePlaceholder)
else if module?.exports?
  module.exports = plugin(simplePlaceholder)
