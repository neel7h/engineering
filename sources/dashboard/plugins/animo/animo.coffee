# FIXME is this plugin still used ? if not, we should remove it
## Actualy, the animo library is used for investigation transitions but not
## the plugin itself.
plugin = (animo) ->
  animo =
    id: 'animo'

  animo

# AMD support (use in require)
if define?.amd?
  define(['animo'], (animo) ->
    return plugin(animo)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.animo = plugin(animo)
else if module?.exports?
  module.exports = plugin(animo)
