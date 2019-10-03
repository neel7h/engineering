TechnicalContext = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  _ = facade._
  t = facade.i18n.t

  TechnicalContextDetailSection = backbone.MetricView.extend({
    className: 'technical-context'
    title: t('Technical properties')
    template: Handlebars.compile('
        <div class="detail-header">
          <div class="close-section"></div>
            <h2>{{title}}</h2>
        </div>
        <div class="object-name"><label>{{t "Name"}}</label><pre>{{name}}</pre></div>
        <div class="object-type"><label>{{t "Type"}}</label><pre>{{type}}</pre></div>
        <div id="table-holder" class="table-computing top-margin"></div>
       ')
    _noTechnicalContextTemplate: Handlebars.compile('<p class="no-context">{{t "No Technical properties available for this object"}}</p>')

    preTemplate: Handlebars.compile('
        <div class="detail-header">
          <div class="close-section"></div>
          <h2>{{title}}</h2>
        </div>
        <div class="object-name"><label>{{t "Name"}}</label></div>
        <div class="object-type"><label>{{t "Type"}}</label></div>
        <div id="table-holder" class="table-computing top-margin">
          <div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div></div>
        </div>
        ')

    initialize: (options)->
      @options = _.extend({},options)
      facade.bus.on('global-filter-change:criticalsOnly',this.render,this)
      return unless @options.component?
      @updateModel(options)

    updateModel: (options)->
      @model = new facade.models.TechnicalContext({
        snapshotId: facade.context.get('snapshot').getId()
        node: options.component
        domain: CENTRAL_DOMAIN
      })

    updateViewState:(parameters)->
      @options.component = parameters.component
      @$el.html(@template({title: @title}))
      facade.ui.spinner(@$el)
      return unless parameters.component?
      @updateModel(parameters)
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload computing details view', e)
      })
      return

    render: ()->
      that = @
      @$el.html(@preTemplate({title: @title}))
      contextResult = @model.getContextResult() if @model
      if contextResult
        setTimeout(()=>
          @$el.html(@template({title: @title, name: contextResult.name, type: contextResult.type.label}))
          return @$el unless @options.component?
          rows = @model?.asRows()

          table = new facade.bootstrap.Table({
            columns:[
              {header:t('Object Property Name'), title:t('Object Property Name'), length: 4,format:(value)->
                return value
              }
              {header: t('Value'), title:t('Value'), align:'center', length: 4, format: (value)->
                return '<span title="'+t(value)+'">' + numeral(value).format('0,000') + '</span>'
              }
            ],
            rows:rows
          })
          if rows.length >0
            @$el.find('#table-holder').html(table.render())
          else
            @$el.find('#table-holder').html(that._noTechnicalContextTemplate())
        , 300)
      @$el
  })

  TechnicalContextCloseSection = backbone.MetricView.extend({
    className: null
    title: t('Technical properties')
    template: Handlebars.compile('
        <div class="detail-header">
          <h2>{{title}}</h2>
          <p class="closed-description">{{t "This section displays numerical information about the selected object e.g. number of lines of code."}}</p>
        </div>
       ')

    initialize: (options)->
      @options = _.extend({},options)

    _render: ()->
      @rendered = true
      @$el.html(@template({title: @title}))
  })

  return {
    TechnicalContextDetailSection
    TechnicalContextCloseSection
  }
