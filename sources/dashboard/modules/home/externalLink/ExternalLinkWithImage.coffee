ExternalLinkWithImage = (facade)->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  ExternalLinkWithImageView = backbone.View.extend({
    className: 'custom-report all-tile-evt'
    template: Handlebars.compile('
        <img title="{{t "click to leave current site and follow the link"}}" src= "{{url}}" class = "external-link-image"/>
        <h3 class="external-link-header" title="{{title}}">{{ellipsisMiddle title data.charBefore data.charAfter}}</h3>
      ')

    events:
      'mousedown': 'clicking'
      'click': 'drillInCustomURL'
      'widget:resize': 'updateRendering'

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

    _setupData:(width)->
      if width < 200
        @large = 'min'
        return _.extend({ charBefore : 15, charAfter : 5})
      if width < 300
        @large = 'medium'
        return _.extend({ charBefore : 20, charAfter : 8})
      @large = 'max'
      return _.extend({ charBefore : 35, charAfter : 15})

    applyToTemplate:(data) ->
      @$el.html(@template({data: data, title: @options.title, url: @options.tile.get('parameters').imageURL}))

    updateRendering:(event) ->
      newData = @_setupData(@$el.width())
      @$el.find('.custom-report all-tile-evt').html(@applyToTemplate(newData))

    render:()->
      newData = @_setupData(@$el.width())
      @$el.find('.custom-report all-tile-evt').html(@applyToTemplate(newData))
      @$el.css('padding','0px')
      @$el
  },{
    processParameters:(parameters)->
      return {
        title: parameters.title
        url: parameters.url
      }
  })

  ExternalLinkWithImageView
