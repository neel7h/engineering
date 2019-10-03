DocumentationSection = (facade) ->

  backbone = facade.backbone
  _ = facade._
  t = facade.i18n.t

  DocumentationSectionView = backbone.View.extend({
    title: t('Rule documentation')
    filterTitles:{
      'quality-rules':t('Rule documentation')
      'quality-measures':t('Measure documentation')
      'quality-distributions':t('Distribution documentation')
    }

    initialize:(options)->
      @options = _.extend({},options)

    updateViewState:(parameters)->
      @options = _.extend({},parameters)
      @render()

    render: ()->
      title = @filterTitles[@options.filter] or @title
      facade.bus.emit('render:documentation', {rule:@options.rule, title:title, $el:@$el})
      @$el
  })

  DocumentationClosedSectionView = DocumentationSectionView.extend({
    render: ()->
      title = @filterTitles[@options.filter] or @title
      facade.bus.emit('render:documentation:summary', {rule:@options.rule, title:title, $el:@$el})
      @$el
  })

  return {
    DocumentationSectionView
    DocumentationClosedSectionView
  }
