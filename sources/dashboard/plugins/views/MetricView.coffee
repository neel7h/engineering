MetricView = ($, _, Backbone)->


  ConfirmDialog = Backbone.View.extend({
    className:'metric-page'
    preTemplate:'<div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate)
      , 500)

    scroll:(event)->
      $(event.target).find('.table').each((index, item)->
        $(item).data('bootstrap-table')?.adjustStickyHeader($(event.target))
      )

    render:()->
      @_render()
      $(window).resize()
      @$el.find('#table-holder').on('scroll', (event)=>
        @scroll(event)
      )
      return @$el

  })
  ConfirmDialog
