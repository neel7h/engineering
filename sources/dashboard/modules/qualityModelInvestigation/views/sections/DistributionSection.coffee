DistributionSection = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span><em title="{{value}}">{{ellipsisMiddle value 15 35}}</em></span>')

  ClosedDistributionSectionView = backbone.View.extend({
    title:t('Distribution of objects')
  })

  DistributionCategoryTable = backbone.View.extend({
    nbRows: 10
    startRow: 1
    template:Handlebars.compile('<h2><span></span>{{t title}}</h2><div class="loading">
                          <div class="square" id="square1"></div>
                          <div class="square" id="square2"></div>
                          <div class="square" id="square3"></div>
                          <div class="square" id="square4"></div>
                        </div>')
    templateWhenData:Handlebars.compile('<h2><span></span>{{t title}}</h2><div id="table"></div>{{#if showMore}}<button>{{t "Show More"}}</button>{{/if}}')
    templateWhenNoData:Handlebars.compile('<p>{{t "No objects in category"}}</p>')
    events:
      'click button': 'showMore'

    initialize:(options)->
      @options = _.extend({},options)
      @options.model.startRow = @startRow
      @options.model.nbRows = @nbRows + 1
      @model.on('sync', @renderData, @)

    showMore: ()->
      @model.pop()
      @startRow = @startRow + @nbRows
      @model.startRow = @startRow
      @model.getData()

    render: ()->
      @$el.html(@template({
        title: @options.title
        theme:@options.theme
      }))

    renderData: ()->
      @$el.html(@templateWhenData({
        title: @options.title
        showMore: @model.size() > @startRow + @nbRows - 1
      }))
      if @model.length == 0
        @$el.find('#table').html(@templateWhenNoData())
      else
        table = new facade.bootstrap.Table({
          columns:[
            {header: t('Object name'), align:'left', format: (value)->
              return _objectNameTemplate({value})
            }
            {header: t('status'), headerMin:'#xe618;', align:'left', format: (value)->
              return '<span>' + value + '</span>'
            }
          ],
          rows:@model.asRows({nbRows: @startRow - 1 + @nbRows, selectedComponent: ''})
        })
        @$el.find('#table').html(table.render())

        qualityRuleHelpviewOptions = {
          $target:@$el.find('th:nth-child(2)')
          isVisible:()=>
            @$el.width() != 0
          useHelpDialog:true
          image:'risk'
          title:t('risk column is defined by the propagated risk index(PRI)')
          content:Handlebars.compile('<p>{{t "This is a measurement of the riskiest objects of the application along with the Health Measures of Robustness, Performance, Security, Changeability and Transferability."}}</p>
            <p>{{t "The PRI formula takes into account the intrinsic risks of the component regarding a selected health measure coupled with the level of use of the given object in the application."}}</p>
            <p>{{t "PRI finds objects that threaten the application usage. Regarding risk identified, it should help you to determine if you need to decide to correct it or not and to correctly anticipate a test planning"}}</p>
            <div><div>{{t "The first RISKIEST(128) object in this illustration has higher PRI because"}}
              <ul><li>1. {{t "More objects depend on it."}}</li>
              <li>2. {{t "...regarding the weight of its violations"}}</li></ul></div>
            <a target="_blank" href="http://doc.castsoftware.com/help/index.jsp?topic=%2F73x%2FAppendix-A---CAST-AIP-Measurement-System-explained_568426852.html">{{t "More information"}} [+]</a></div>')()
        }
        facade.bus.emit('help:createView',qualityRuleHelpviewOptions)
        @$el
  })

  DistributionSectionView = backbone.View.extend({
    title: t('Distribution of objects')
    _SelectedObjectTemplate: Handlebars.compile('<h2>{{title}}</h2><h3>{{name}}</h3>')
    template: Handlebars.compile('
                      <div class="detail-header">
				          <div class="close-section"></div>
                          <h2>{{title}}</h2>
                      </div>
                      <div class="detail-actions">
                      </div>
                      <div id="table-holder" class="table-distribution">
                        {{#each categories}}
                        <div class="category category-{{key}}" id="category-{{index}}"></div>
                        {{/each}}
                  </div>
                  <footer></footer>')

    initialize: (options)->
      @updateModel(options)
      @t = facade.i18n.t

    updateModel: (options)->
      @options = _.extend({}, options)
      @model = new facade.models.Distribution({
        applicationHref: window.SELECTED_APPLICATION_HREF
        moduleHref:facade.context.get('module')?.get('href')
        domain:CENTRAL_DOMAIN
        snapshotId: facade.context.get('snapshot').getId()
        qualityDistributionId: @options.rule
        businessCriterion:@options.business
      })

    updateViewState:(parameters)->
      @$el.html(@template({title: @title}))
      facade.ui.spinner(@$el)
      @updateModel(parameters)
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload distribution', e)
      })
      return

    render: ()->
      @$el.html(@template({
        title: @title
        theme:@options.theme
        categories: [
          {key:'very-high',index:1},
          {key:'high',index:2},
          {key:'medium',index:3},
          {key:'low',index:4}
        ]
      }))
      for i in [1..4]
        ((i)=>
          $category = @$el.find('#category-' + i)

          options = _.extend({}, @options, @model.getCategoryModel(i))
          categoryView = new DistributionCategoryTable(options)
          $category.html(categoryView.render())
          $category.find('h2').html(@t($category.find('h2').text()))
          categoryView.model.getData()
        )(i)
      @$el

  })

  return {
    ClosedDistributionSectionView
    DistributionSectionView
  }
