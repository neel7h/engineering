ExternalLink = (facade)->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  ExternalLinkView = backbone.View.extend({
      className: 'custom-report all-tile-evt'
      template: Handlebars.compile('
        <div title="{{t "click to leave current site and follow the link"}}" class="follow-link"></div>
        <h3>{{title}}</h3>
      ')

      events:
        'mousedown':'clicking'
        'click':'drillInCustomURL'

      clicking:(event)->
        @clicked = {
          x: event.pageX
          y: event.pageY
        }
        true

      drillInCustomURL:(event)->
        if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
          @clicked = null
          return if @$el.hasClass('no-value')
          return if 'close' == event.target.className
          window.open @options.url, "_blank"
        @clicked = null

      initialize:(options)->
        @options = _.extend({},options)

      render:()->
        @$el.html(@template({
            title:@options.title
        }))
        @$el

  },{
    processParameters:(parameters)->
      return {
        title:parameters.title
        url:parameters.url
      }
  })

  return ExternalLinkView
