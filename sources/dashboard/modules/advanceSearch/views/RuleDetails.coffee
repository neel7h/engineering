RuleDetails = (facade) ->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  selectedRows = {'business-criteria':[],'technical-criteria':[],'quality-rules':[],'technology':[],'name':[],'weight':[],'critical':[],'status':[],'transactions':[]}

  backbone.SectionContainerView.extend({
    bus: facade.bus
    localId: 'as_'
    initialize: (options)->
      options.facade = facade

      backbone.SectionContainerView.prototype.initialize.apply(this, arguments)
    sections: [
      {
        id: 'violations'
        title: t('Violations')
        openedByDefault: true
        View: backbone.ViolationDetailView.ObjectViolationSectionView.extend({
          title: t('Violations')
          theme: 'background-blue'
          events:
            'click .export': 'downloadAsExcelFile'

          selectedItems:(item)->
            if item.extra.model?.type
              selectedRows[item.extra.model.type].push(item.extra.model.reference.key)
            else if item.type == 'name'
              selectedRows['name'].push(item.extra.model.moduleSnapshot.name)
            else if item.type == 'technology'
              selectedRows['technology'].push(item.extra.model.technology)
            else if item.type == 'weight'
              selectedRows['weight'].push(item.extra.model)
            else if item.type == 'critical'
              selectedRows['critical'].push(item.extra.model)
            else if item.type == 'status'
              selectedRows['status'].push(item.extra.model)
            else
              selectedRows['transactions'].push(item.extra.transaction)

          objectSearch:(that)->
            fetchData:()->
              that.options.subString = @fetchData["arguments"][0].currentTarget.value
              that.filterSearchData()
              that.model = new facade.models.violations.AdvanceSearchViolations([], {
                applicationHref: window.SELECTED_APPLICATION_HREF
                snapshotId: facade.context.get('snapshot').getId()
                subString: that.options.subString
                nbRows: that.nbRows
                startRow: 1
                filterSearch: that.options.filterSearch
              })
              that.model.getData({
                success:()=>
                  that.updateViewState(that.options)
              })

          filterSearchData:()->
            selectedRows[@options.selectedType] = []
          #remove local storage from navigating to other page
#            if localStorage.selectedCriteria?
#              rowsSelected = JSON.parse(localStorage.selectedCriteria)
#              rowsSelected.map((item)=> @selectedItems(item))

          callModel: ()->
            @filterSearchData()
            @EducationModel = new facade.models.education.EducationSummary([], {
              href: facade.context.get('snapshot').get('href')
            })
            @model = new facade.models.violations.AdvanceSearchViolations([], {
              applicationHref: window.SELECTED_APPLICATION_HREF
              snapshotId: facade.context.get('snapshot').getId()
              nbRows: @nbRows
              subString: @options.subString
              startRow: 1
              status: @status
              filterSearch: @options.filterSearch
            })
            @totalViolationsModel = new facade.models.violations.TotalViolations([], {
              applicationHref: window.SELECTED_APPLICATION_HREF
              snapshotId: facade.context.get('snapshot').getId()
            })

          updateModel: (options)->
            @options = _.extend({}, options)
            @startRow = 1
            @component = @options.component
            @model = new facade.models.violations.AdvanceSearchViolations([], {
              applicationHref: window.SELECTED_APPLICATION_HREF
              snapshotId: facade.context.get('snapshot').getId()
              nbRows: @nbRows
              startRow: @startRow
              subString: @options.subString
              status:@status
              filterSearch: @options.filterSearch
            })

          getViolationAndRenderShowMore:(options)->
            el = @$el if @$el?
            @filterSearchData()
            @options = _.extend({}, options)
            violationRatio = @model.models.slice(-1)[0]?.get('number')
            @_renderShowMoreSelector(el, violationRatio, @nbRows)

          tableViewState: (options)->
            @table?.select('component', @options.component, true)

          generateMessage: ()->
            return ''
        })
      }
    ]
  })