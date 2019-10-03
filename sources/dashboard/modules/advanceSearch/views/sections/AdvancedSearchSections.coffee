AdvancedSearchSections= (facade)=>

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  selectedRows = {'business-criteria':[],'technical-criteria':[],'quality-rules':[],'technology':[],'name':[],'weight':[],'critical':[],'status':[],'transactions':[]}

  _objectNameTemplate = Handlebars.compile('<span>
    <em class="short-content" title="{{shortValue}} ({{value}})">{{ellipsisMiddle value 20 30}}</em>
    <em class="large-content" title="{{shortValue}} ({{value}})">{{ellipsisMiddle value 40 60}}</em>
    <em class="super-large-content" title="{{shortValue}} ({{value}})">{{value}}</em>
  </span>')

  CriteriaOrRulesSection = backbone.View.extend({
    header: t('All Criteria and Rules')
    title: t('Criteria or rules')
    criteria: t('criteria or rules')
    template: Handlebars.compile('<div class="search-box"><div class="filter-search">
                <input type="text" placeholder="{{t "Contain"}}" id="advancedSearch-filter" />
              </div></div>
              <div id="table-holder"></div>')

    events:
      'keyup #advancedSearch-filter': 'filterList'

    initialize:()->
      @model = new facade.models.advancedSearch.CriteriaResult([],href:facade.context.get('snapshot').get('href'))
      facade.bus.on('clearSearch', @resetSelectedRows, @)

    resetSelectedRows: () ->
      _.each(Object.keys(selectedRows), (row) -> selectedRows[row] = [])
      localStorage.setItem('resetSelector', false)

    getTableRows:() ->
      @table.options.rows.models

    selectedBox: (data)->
      selectedRows['business-criteria'] =[]
      selectedRows['technical-criteria'] =[]
      selectedRows['quality-rules'] =[]
      _.each(data, (item)-> selectedRows[item.get('extra').model.type].push(item.get('extra').model.reference.key))

    onSelection:(options)->
      $tableHolder = @$el?.find('#table-holder')
      if @$el.find('#advancedSearch-filter').val()?.length and @$el.find('#toggle-header:checked').val() == "on"
        for i in[0 .. @getTableRows().length-1]
          if @$el.find('table tbody tr[data-index="'+ i + '"] :visible').length == 0
            @getTableRows()[i].attributes.rowSelected = false
      data = @table.getSelectedRows()
      #remove local storage from navigating to other page
#      localStorage.setItem("selectedCriteria", JSON.stringify(data))
      localStorage.setItem('selectedRows',JSON.stringify(data))
      value = data.length
      if value != 0
        @$el.parents('section').children('.detail-header').find('p .count').html('<b>:</b>' + ' ' + value)
      else
        @$el.parents('section').children('.detail-header').find('p span').text('')
      if $('.count b').length
        $('.clear-section').removeClass('disabled').parent().removeAttr('title') and $('.option-drop-down').removeClass('inactive')
      else
        $('.clear-section').addClass('disabled').parent().attr('title',t('No filter selected')) and $('.option-drop-down').addClass('inactive')
      if $tableHolder.find('tbody tr:visible input[type="checkbox"]:checked').length == $tableHolder.find('tbody tr:visible').length
        $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', true)
      @resetSelectedRows() if JSON.parse(localStorage.getItem('resetSelector'))
      @selectedBox(data)
      facade.bus.emit('filterSearch',{
        filterSearch: selectedRows,
        selectedType: options.row?.get('type'),
        pageId: 'advanceSearch',
        filterBusinessCriterion: '60017',
        theme: 'background-blue'
      })

    filterList:(event)->
      filter = $(event?.target).val() or @$el.find('#advancedSearch-filter').val()
      if @$el.find('#advancedSearch-filter').val()?
        $tableHolder = @$el.find('#table-holder')
        $tableHolder.find('tbody tr').show()
        $tableHolder.find('tbody .no-violations').remove()
        $tableHolder.removeClass('no-criteria')
        $tableHolder.find('th:first').removeClass('hide-row').attr('title', t('Select all currently displayed'))
        rows  = _.reject($tableHolder.find('tbody tr'),(row) ->
          return row if $(row).text().toLowerCase().includes(filter.toLowerCase()))
        _.each(rows,(row)-> $(row).hide())
        data = _.map(JSON.parse(localStorage.getItem('selectedRows')), (data) -> data.id)
        _.each $tableHolder.find('tbody tr:visible'), (row, index) ->
          if !_.include(data, $(row).attr('data-id'))
            $(row).children('td:first').children('input').prop('checked', false)
          return
        if $tableHolder.find('tbody tr:visible input[type="checkbox"]:checked').length == $tableHolder.find('tbody tr:visible').length
          $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', true)
        else $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', false)
        if rows.length == @model._collection?.length or rows.length == @model.models?.length
          $tableHolder.find('tbody').append('<div class="no-violations">' + t('No') + ' ' + @criteria + ' ' + t('found matching your search') + '</div>')
          $tableHolder.find('th:first').addClass('hide-row').attr('title', t('No') + ' ' + @criteria + ' ' + t('available'))
          $tableHolder.addClass('no-criteria')
          $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', false)

#remove local storage from navigating to other page
#    tableRows:()->
#      rowsSelected = _.map(JSON.parse(localStorage.selectedCriteria),(row)->return row.extra.model?.reference?.key) if localStorage.selectedCriteria?
#      rows = @model.asRows()
#      _.each(rows.models, (row, index)->
#        rows.models[index].set('id', rows.models[index].get('extra').model?.reference?.key)
#        if _.contains(rowsSelected,row.get('id'))
#          row.set({'rowSelected': true}))

    renderTableElements:()->
      $tableHolder = @$el?.find('#table-holder')
      $tableHolder.html(@table.render())
      $tableHolder.removeClass('no-criteria')
      @table.on('update:row-selector', @onSelection, @)
      @table.on('sorted', @filterList, @)
      @$el.find('thead span').css('pointer-events','none') if @title == t('Criteria or rules')
      if $tableHolder.find('tbody tr:visible input[type="checkbox"]:checked').length == $tableHolder.find('tbody tr:visible').length
        $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', true)
      $tableHolder.find('thead:first input[type="checkbox"]').prop('checked', false)

    render:(filterSection)->
      @rendered = true
      @$el.html(@template({title: @title}))
      $tableHolder = @$el?.find('#table-holder')
      facade.ui.spinner($tableHolder)
      $tableHolder.addClass('no-criteria')
      if filterSection.attr('id') == 'sec_weight' or filterSection.attr('id') == 'sec_critical' or filterSection.attr('id') == 'sec_status' then rows =  @asRows() else rows = @model.asRows()
      columns = if filterSection.attr('id') == 'sec_transactions' then [{header: @header, format:(value, columnId, rowId, item)->
        return _objectNameTemplate({value:value, shortValue:item.extra.shortName})
      }]
      else [{header: @header}]
      @model.getData({
        success:()=>
          @table = new facade.bootstrap.Table({
            rowSelector: true
            columns: columns
            rows: rows
          })
          @renderTableElements()
      })
      @$el
  })
  TechnologiesSection = CriteriaOrRulesSection.extend({
    title: t('Technologies')
    header: t('All Technologies')
    template: Handlebars.compile('<div id="table-holder"></div>')

    initialize:()->
      @model = new facade.models.advancedSearch.TechnologiesResult([],href:facade.context.get('snapshot').get('href'))

    selectedBox: (data)->
      selectedRows['technology'] = []
      _.each(data, (item)-> selectedRows['technology'].push(item.get('extra').model.technology))
  })

  ModulesSection = CriteriaOrRulesSection.extend({
    title: t('Modules')
    header: t('All Modules')
    template: Handlebars.compile('<div id="table-holder"></div>')

    initialize:()->
      @model = new facade.models.advancedSearch.ModulesResult([],href:facade.context.get('snapshot').get('href'))

    selectedBox: (data)->
      selectedRows['name'] = []
      _.each(data, (item)-> selectedRows['name'].push(item.get('extra').model.moduleSnapshot.name))
  })
  WeightSection = CriteriaOrRulesSection.extend({
    title: t('Weight')
    header: t('All Weight')
    template: Handlebars.compile('<div id="table-holder"></div>')

    selectedBox: (data)->
      selectedRows['weight'] = []
      _.each(data, (item)-> selectedRows['weight'].push(item.get('extra').model))

    asRows:()->
      results = new backbone.Collection()
      for weight in [0..9]
        results.push({
          columns: [weight]
          type: "weight"
          extra: {
            model: weight
          }
        })
      results
  })

  CriticalSection = CriteriaOrRulesSection.extend({
    title: t('Criticality')
    header: t('All')
    template: Handlebars.compile('<div id="table-holder"></div>')

    selectedBox: (data)->
      selectedRows['critical'] = []
      _.each(data, (item)-> selectedRows['critical'].push(item.get('extra').model))

    asRows:()->
      results = new backbone.Collection()
      criticity = [t('critical'), t('non critical')]
      for value in criticity
        results.push({
          columns: [value]
          type: "critical"
          extra: {
            model: value
          }
        })
      results
  })

  ViolationStatusSection =  CriteriaOrRulesSection.extend({
    title: t('Violation Status')
    header: t('All Status')
    template: Handlebars.compile('<div id="table-holder"></div>')

    selectedBox: (data)->
      selectedRows['status'] = []
      _.each(data, (item)-> selectedRows['status'].push(item.get('extra').model))

    asRows:()->
      results = new backbone.Collection()
      violations = [t('added'), t('updated'),t('unchanged')]
      for value in violations
        results.push({
          columns: [value]
          type: "status"
          extra: {
            model: value
          }
        })
      results
  })

  TransactionsSection = CriteriaOrRulesSection.extend({
    title: t('Transactions')
    header: t('All Transactions')
    criteria: t('transactions')

    initialize:(options)->
      @options = _.extend({
        context: 60017
        nbRows: '$all'
      }, options)
      @model = new facade.models.transactions.TransactionsListing([],{
        href:SELECTED_APPLICATION_HREF
        snapshotId: facade.context.get('snapshot').getId()
        context: @options.context
        nbRows: @options.nbRows
      })

    selectedBox: (data)->
      selectedRows['transactions'] = []
      _.each(data, (item)-> selectedRows['transactions'].push(item.get('extra').transaction))

  })

  return {
    CriteriaOrRulesSection
    TechnologiesSection
    ModulesSection
    WeightSection
    CriticalSection
    ViolationStatusSection
    TransactionsSection
  }