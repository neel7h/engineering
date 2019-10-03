ViolationDetails = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  t = facade.i18n.t

  SourceCodesView = backbone.View.extend({
    title:t('Source code')
    template:Handlebars.compile('<div class="sections">
      <div class="sections-content">
        <section class="detail-header">
          <h2>{{t "Source code"}}</h2>
          <p class="no-violations">{{t "No violating object is available for violation details to display."}}</p>
        </section>
      </div>
    </div>')

    initialize:(options)->
      @options = _.extend({},options)

    updateViewState:(options)->
      if @options.component == options.component
        return if @options.rule == options.rule
      @options = _.extend({},options)
      @render()
      return

    render: ()->
      if 'none' == @options.component
        @$el.html(@template())
      else if '7156' ==  @options.rule
        facade.bus.emit('render:copyPasteFindings', {
            ruleComponent:@options.component
            rule:@options.rule
            $el:@$el
            container:@
        })
      else
        facade.bus.emit('render:sourceCode', {
          ruleComponent:@options.component,
          rule:@options.rule
          title:@title, $el:@$el, container:@
        })
      @$el
  })
