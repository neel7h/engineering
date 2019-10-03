CoreTiles = (facade)->
  Backbone = facade.backbone
  Handlebars = facade.Handlebars
  t = facade.i18n.t

  InactiveTileView = Backbone.View.extend({
      className: 'error-tile all-tile-evt'
      template: Handlebars.compile('
        <h2>{{title}}</h2>
        <h3>{{t "not available for past snapshot"}}</h3>
        <p title="{{t "The data you are trying to display is not available for current application or snapshot"}}">{{t "Data currently not available"}}</p>
      ')

      render:()->
        @$el.html(@template({
            title:this.constructor.title or t('Unavailable')
        }))
        return @$el
  })

  TileNotFoundView = Backbone.View.extend({
      className: 'error-tile all-tile-evt'
      template: Handlebars.compile('
        <h2>{{t "Tile misconfiguration"}}</h2>
        <p title="We were not able to find the configured tile. Please verify your configuration.">{{t "Tile configured not found."}}</p>
      ')

      render:()->
        @$el.html(@template())
        return @$el
  })

  return {
    InactiveTileView
    TileNotFoundView
  }
