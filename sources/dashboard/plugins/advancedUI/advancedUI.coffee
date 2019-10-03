plugin = ($) ->

  # switch plugin
  $.fn.switch = (options)->
    settings = $.extend(true, $.fn.switch.settings, options);
    this.each(()->
      $dialog = $('<input type="checkbox" class="tile-switch" /><div/>')
      $dialog.prop('checked', settings.on)
      $($dialog[1]).on('click', ()->
        $($dialog[0]).prop('checked', !$($dialog[0]).prop('checked'))
      )
      $dialog.appendTo(this);
    )
  $.fn.switch.settings = {
    on: false
  }

  advancedUI =
    id: 'animo'
    Facade:
      advancedUI:
        switch:(options)->
          return unless options?.$el?
          return options.$el.switch({on:options.on})
        cloud:($el, words)->
          # FIXME why not use a class here ?
          $el.css('position', 'absolute')
          $el.css('bottom', '10px')
          $el.css('right', '10px')
          $el.css('left', '10px')
          $el.css('margin-top', '10px')
          $el.jQCloud(words,{
            autoResize:true
            shape:'elliptic'
            delay:1
            removeOverflowing:true
            steps:10
            afterCloudRender:()->
              this.find('span').each((index, item)->
                $item = $(item)
                id = $item.prop('id').split('_')
                index = parseInt(id[id.length-1]) # index and list order is not preserved by jqcloud
                $item.attr('title', words[index]?.fullName)
              )
          })



  advancedUI

# AMD support (use in require)
if define?.amd?
  define(['jquery', 'jQCloud'], ($) ->
    return plugin($)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.advancedUI = plugin($)
else if module?.exports?
  module.exports = plugin($)
