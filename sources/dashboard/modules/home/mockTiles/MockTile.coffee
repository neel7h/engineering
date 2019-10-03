MockTile = (facade) ->

  Handlebars = facade.Handlebars
  
  return facade.backbone.View.extend({
    className:'error-tile all-tile-evt'
    template:Handlebars.compile('
      <div class="title">{{t title}}</div>
    ')

    initialize:(options)->
      @t = facade.i18n.t
      @options = _.extend({},options)

    render:()->
      titleText = @options.tile.get('title')
      @$el.html(Handlebars.compile(@template({title: @t(titleText)})))
   })
