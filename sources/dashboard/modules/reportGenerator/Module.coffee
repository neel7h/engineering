define [], ->
  ReportGeneratorModule = (facade) ->
    Handlebars = facade.Handlebars
    $ = facade.$
    t = facade.i18n.t
    _ = facade._

    _objectNameTemplate = Handlebars.compile('<span>
          <em class="short-content" title="{{value}}">{{ellipsisMiddle value 35 45}}</em>
          <em class="large-content" title="{{value}}">{{ellipsisMiddle value 45 55}}</em>
          <em class="super-large-content wrappable " title="{{value}}">{{value}}</em>
         </span>')

    _violationsTemplate = Handlebars.compile('<span>
         {{#if href}}
          <em class="short-content" title="{{title}}"><a class="{{state}}" href="{{href}}">&#xe91a;</a></em>
         {{else}}
          <em class="short-content" title="{{title}}"><a class="{{state}}">&#xe91a;</a></em>
         {{/if}}
         </span>')

    ReportGeneratorView = facade.backbone.View.extend({

      reportTemplate: Handlebars.compile('{{#if data}}<div class="generateButton"><button class="submit">{{t "Generate Report"}}</button></div>
                        <div class="loader"><div class="title"></div><div class="load"><div class="bar"></div></div></div>
                      {{else}}
                        <div class ="report-overview"><div class="headerTitle"></div>
                          <div class="export"><a title="{{t "download data as excel file"}}" class="download-file">{{t "Download Excel"}}</a></div>
                          <div id="table-holder" class="table-holder"></div>
                          <div id="show-more"></div>
                        </div>
                      {{/if}}')

      template:Handlebars.compile('<div class="reportsSelector header" id="reportsSelector">
                  <div class="report"><span><h4 class="large">{{t "Report Category"}}</h4><div class= "reportCategory dataSelector" id="reportCategory"></div></span></div>
                  <div class="reportType"><span><h4 class="large">{{t "Report Type"}}</h4><div class= "dataSelector" id="reportType"></div></span></div>
                <div class="reportData"></div></div>')

      loadingTemplate: '<div class="loading"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

      events:
        'click .submit': 'generateReport'
        'click .download-file': 'downloadAsExcelFile'

      preRender: ()->
        @$el.find('#table-holder').html(@loadingTemplate)
        @$el.find('.download-file').addClass('disabled ')
        @$el.find('#show-more').hide()

      initialize: (options) ->
        @el = options.el
        @businessCriterion = "60017"

      showMore: (nbRows)->
        el = @$el
        @nbRows = nbRows
        @startRow = @modelResult.size() + 1
        @modelResult.startRow = @startRow
        @modelResult.nbRows = @nbRows
        @modelResult.getData({
          success: ()=>
            @_updateTableRender(el)
        })

      _updateTableRender:(el)->
        rows = @modelResult.asRows({nbRows: @startRow - 1 + @nbRows})
        @table.$el.detach()
        @table.update({rows: rows})
        @table.options.rows = rows
        el.find('.loading').remove()
        el.find('#table-holder').append(@table.render())
        @$el.find('.download-file').removeClass('disabled')
        @table.delegateEvents()
        @_renderShowMoreSelector(el, @violationRatio , @startRow- 1 + @nbRows)
        @_hideOrShowShowMoreButton()

      _hideOrShowShowMoreButton:()->
        tableSize = @modelResult.length
        $('#show-more').css('display', 'table') if tableSize >= 20
        $('#show-more').css('display', 'none') if tableSize == @violationRatio

      renderShowMore:(el, callback)->
        that = this
        @model.getData({
          success: () =>
            if @reportType == "correctedViolations" then @violationRatio = @model.models[0].get('removedViolation') else @violationRatio = @model.models[0].get('addedViolation')
            if @violationRatio?
              that._renderShowMoreSelector(el, @violationRatio, that.startRow - 1 + that.nbRows)
            else
              that._renderShowMoreSelector()
            callback();
        })

      showOptionsOnTopOrBottomForReport:()->
        menu = $('.cont', '#show-more').first()
        if menu?
          $(menu).removeClass('top')
          menuTop = menu.offset()?.top
          menuHeight = menu.height()
          totalMenuHeight = menuTop + menuHeight
          if totalMenuHeight >= $(window).height()
            $(menu).addClass('top')

      pushMenuItems:(menuItems, value)->
        item = if isNaN(value) then value else t('+' + value)
        menuItems.push({text: item, action: ()=>
          @preRender()
          if isNaN(value) then @showMore(1000000) else @showMore(value)
        })

      _renderShowMoreSelector:(el, violationRatioValue, nbRows)->
        allText = t('All')
        if violationRatioValue?
          allText = allText + " ("+ violationRatioValue + ")"
        violationsCount = facade.portal.get('configuration').violationsCount or 5000
        if ((violationRatioValue > violationsCount and violationRatioValue < 100) or  violationRatioValue > violationsCount)
          allTextTemplate = Handlebars.compile('<span title="{{t "You cannot display a high number of violations without big performance issues"}}">'+ allText + '</span>')
        else
          allTextTemplate = Handlebars.compile('<span title="{{t "Depending on the number of violations, this request can take time"}}">'+ allText + '</span>')
        menuItems =[]
        if nbRows < violationsCount
          @pushMenuItems(menuItems, 10) if violationRatioValue > 30
          @pushMenuItems(menuItems, 100) if violationRatioValue > 120 and (violationsCount - nbRows) > 100 and (violationRatioValue - nbRows) > 100
        @pushMenuItems(menuItems,allTextTemplate)
        @showMoreMenu = new facade.bootstrap.Menu({
          text:t('Show More')
          class: 'light-grey'
          items: menuItems
        });
        el.find('#show-more').html(@showMoreMenu.render())
        @showOptionsOnTopOrBottomForReport()
        if nbRows >= violationsCount
          el.find('#show-more li')[0]?.classList.add('inactive')
        if violationRatioValue > violationsCount and (violationRatioValue < 100 or (violationsCount - nbRows) < 100)
          el.find('#show-more li')[1]?.classList.add('inactive')
        else if violationRatioValue > violationsCount
          el.find('#show-more li')[2]?.classList.add('inactive')
        el.find('#show-more li.selectable.no-separator.inactive').prop("disabled", true)

      fetchModeldata: (reportType)->
        switch reportType
          when 'newViolations', 'correctedViolations'
            secondHeader = t('Object name location')
            return {
              model: facade.models.reportGenerator.CorrectedViolationsReport
              modelCount:facade.models.reportGenerator.CorrectedAndRemovedViolationCount
              status: 'added' if reportType == 'newViolations'
              firstHeader: t('Rule Name')
              secondHeader: secondHeader
              secondHeaderTitle: secondHeader
              thirdHeader: t('Status')
              violations: true
              align: 'left'
              showMore: true
            }

          when 'cyclomaticComplexityHighFanout', 'cyclomaticComplexityLowDocumentation'
            model = facade.models.reportGenerator.ComplexityFanOutReports
            thirdHeader = t('Fan-Out')
            secondHeader= t('Cyclomatic Complexity')
            if reportType == 'cyclomaticComplexityLowDocumentation'
              model = facade.models.reportGenerator.LowDocumentationReports
              thirdHeader = t('Documentation Ratio')
            return{
              model: model
              firstHeader: t('Object name location')
              secondHeader: secondHeader
              secondHeaderTitle: secondHeader
              thirdHeader: thirdHeader
              violations: true
              align: 'left length-1'
            }

          when 'rulesWithLargestDecreaseNumberViolations', 'rulesWithLargestIncreaseNumberViolations', 'rulesWithLargestDecreasePercentageViolations', 'rulesWithLargestIncreasePercentageViolations'

            secondHeader = t('Variation')
            secondHeader = t('% Variation') if reportType == 'rulesWithLargestDecreasePercentageViolations' or reportType == 'rulesWithLargestIncreasePercentageViolations'
            filterCriterion = ''
            filterCriterion = 'removed' if reportType == 'rulesWithLargestDecreaseNumberViolations'
            filterCriterion = 'added'   if reportType == 'rulesWithLargestIncreaseNumberViolations'

            return{
              ruleViolation: true
              model: facade.models.TopRulesViolationsResults
              firstHeader: t('Rule Name')
              align: 'left length-1'
              secondHeader: secondHeader
              secondHeaderTitle: secondHeader
              filterCriterion: filterCriterion
            }

          when 'rulesWithHighestImprovementOpportunities'
            return{
              model: facade.models.reportGenerator.ImprovementGap
              firstHeader: t('Rule Name')
              secondHeader: t('Improvement Gap')
              secondHeaderTitle: t('Improvement gap is the indicator of the highest improvement opportunity. It is calculated based on the Rule weight, Technical Criteria weight multiplied by the gap between the highest grade and the current grade.')
              align: 'left length-1'
            }

      generateProjectReport:(reportType, reportValue, options)->
        @$el.find('.headerTitle').text(reportValue)
        @$el.find('.download-file').removeClass('disabled')
        globalOptions = facade.portal.get('configuration').parameters or {nbRows:10}
        @options = _.extend({}, options)
        @options.business = 60017
        snapshot = facade.context.get('snapshot')
        @startRow=1
        @nbRows= globalOptions.nbRows
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
        @preRender()
        @fetchModel= @fetchModeldata(reportType)
        $tableHolder = @$el.find('#table-holder')
        @modelData = {
          href: window.SELECTED_APPLICATION_HREF,
          status: @fetchModel.status
          business: @options.business
          snapshotId: snapshot.getId()
          technicalCriterion: 'all'
          lastTwoSnapshotIds: lastTwoSnapshotIds
          startRow:@startRow
          nbRows:@nbRows
        }

        @model = new @fetchModel.modelCount([],{href: window.SELECTED_APPLICATION_HREF,status: @fetchModel.status, snapshotId: snapshot.getId(), business: @options.business}) if @fetchModel.showMore
        @modelResult = new @fetchModel.model([],@modelData)
        @modelResult.getData({
          success:()=>
            that = @
            if @fetchModel.ruleViolation
              filterCriterion = @fetchModel.filterCriterion
              rules = @modelResult.filterRules({filterCriterion, reportType})
              rows = @modelResult.asRows(rules, filterCriterion)
            else
              rows = @modelResult.asRows(reportType)
            columns = [
              {header: @fetchModel.firstHeader, headerMin:'#xe61a;', title: @fetchModel.firstHeader, align: 'left' , format: (value)->
                return _objectNameTemplate({value})
              },
              {header: @fetchModel.secondHeader, title: @fetchModel.secondHeaderTitle, align: @fetchModel.align, format: (value)->
                return _objectNameTemplate({value}) if reportType == 'newViolations' || reportType == 'correctedViolations'
                if filterCriterion == 'removed' then value = '-'+ value else if filterCriterion == 'added' then value = '+'+ value
                value = facade.tableHelpers.formatWeight(value) if reportType == 'rulesWithHighestImprovementOpportunities'
                value = facade.tableHelpers.formatVariation(value, null, true) if reportType == 'rulesWithLargestDecreasePercentageViolations' or reportType == 'rulesWithLargestIncreasePercentageViolations'
                return '<span>' + value + '</span>'
              },
              {header: @fetchModel.thirdHeader, title: @fetchModel.thirdHeader, align: @fetchModel.align , format: (value)->
                value = numeral(value).format('0.00') if reportType == 'cyclomaticComplexityLowDocumentation'
                return '<span>' + value + '</span>'
              },
              {header: t(''), align:'center', format: (value)->
                state = 'showViolation'
                if value.includes('/')
                  title = t('Access the violation source code')
                  value += '/_rg'
                else
                  title = t('Access the rule')
                  value += '/0/_rg'
                href = '#' + SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' + that.businessCriterion + '/all/' + value
                return  _violationsTemplate({href: href, title: title, state: state})
              }
            ]
            switch reportType
              when 'rulesWithHighestImprovementOpportunities', 'rulesWithLargestDecreaseNumberViolations', 'rulesWithLargestIncreaseNumberViolations', 'rulesWithLargestDecreasePercentageViolations', 'rulesWithLargestIncreasePercentageViolations'
                columns.splice(2,1)

              when 'cyclomaticComplexityHighFanout', 'cyclomaticComplexityLowDocumentation', 'correctedViolations'
                columns.splice(3)

            @table = new facade.bootstrap.Table({
              columns: columns
              rows: rows
            })
            @columns = @table.options.columns
            @count = @columns.length
            @columns.filter((item) => @count--  if item.header == undefined)
            @columns.splice(@count)
            if @fetchModel.violations then @noViolation = t('No violations found') else @noViolation = t('No rules found')
            if @fetchModel.showMore
              @renderShowMore(@$el, () =>
                $tableHolder.html(@table.render())
                @NoViolationsFound()
                @_hideOrShowShowMoreButton()
              )
              $('#drill-page').on('scroll', () =>
                @showOptionsOnTopOrBottomForReport()
              )
              $(window).on('resize', () =>
                @showOptionsOnTopOrBottomForReport()
              )
            else
              $tableHolder.html(@table.render())
              @NoViolationsFound()
        })

      NoViolationsFound:() ->
        @$el.find('.download-file').removeClass('disabled')
        @$el.find('table thead tr:first th.center').addClass('violation-header-size')
        @table.on('sorted', @sortColumn, @)
        if @modelResult._collection.length == 0
          @$el.find('.table-holder table tbody').append('<div class="no-violations">' + @noViolation + '</div>')
          @$el.find('.download-file').addClass('disabled')

      sortColumn:() ->
        if @modelResult._collection.length == 0
          @$el.find('.table-holder table tbody').append('<div class="no-violations">' + @noViolation + '</div>')
          @$el.find('.download-file').addClass('disabled')

      downloadAsExcelFile:()->
        href = @modelResult.url() +  '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        $.ajax('url': REST_URL + 'user', 'async': false)
          .success(()->
          window.location = href if href?
        )
        return false

      fetchData: (results) ->
        data = []
        for report in results
          label = report.templateLabel
          value = report.templateId
          selected = if @reportType == value or @reportCategory == value then true else false
          data.push({
            label: t(label)
            value: value
            selected: selected
          })
        return new facade.bootstrap.Selector({data: data, class: 'light-grey', maxCharacters:20})

      fetchReportType:(categoryChanged) ->
        @templates = _.find(facade.portal.get('configuration').reportCategory, (category) => return category if category.id == @reportCategory)
        @reportType = localStorage.getItem('reportType')
        @reportType = null if (categoryChanged and JSON.parse(localStorage.getItem('reportGenerating')) == false) or localStorage.getItem('reportCategory') != @reportCategory
        @$el.find('.reportType').show()
        reportType = @fetchData(@templates.reportTemplates)
        _.filter(reportType.options.data ,(reportData)=>
          if @reportType == undefined or @reportType == null
            @reportType = reportData.value
            @reportValue  = reportData.label
          if reportData.value == @reportType
            reportData.selected = true
            @reportType = reportData.value
            @reportValue  = reportData.label
        )
        $appType = @$el.find('#reportType')
        $appType.html(reportType.render())
        if localStorage.reportGenerating =='true' then @showLoader() else $('.loader').hide()
        @$el.find('#reportType .cont .options').attr('data-before', t('Select a report type'))
        @generateProjectReport(@reportType, @reportValue) if @templates.id == 'miscellaneous'
        reportType.on('selection', (data)=>
          return if data == @reportType
          selectedReport = _.find(@templates.reportTemplates, (template) -> return template if template.templateId == data)
          @reportType = selectedReport.templateId
          @reportValue  = selectedReport.templateLabel
          @generateProjectReport(@reportType, @reportValue) if @templates.id == 'miscellaneous'
        )

      rotate: (selector) ->
        @$el.find(selector).animate({ left: @$el.find('.load').width() }, 1000, =>
          @$el.find(selector).css 'left', -@$el.find(selector).width() + 'px'
          @rotate selector
        )
      notificationMessage:(jqXHR)->
        message = t('Failed to Generate report ') + @reportValue + '</br>'
        message += jqXHR.responseJSON.message.cause if jqXHR.status == 500
        if jqXHR.status == 503
          message += jqXHR.responseJSON.message.cause if jqXHR.responseJSON?
          message +=  'Service Unavailable' if !jqXHR.responseJSON?.message.cause
        if jqXHR.status == 200
          message = @reportValue + t(' Generated Successfully')
        facade.bus.emit('notification:message',{
          message: Handlebars.compile('<span class="toast-message">' + message + '</span>')
          title: '<em>'+t('REPORT')+'</em> '
          type: 'log'
        })

      showLoader:()->
        @$el.find('.loader').show()
        @$el.find('.loader .title').text(t('Preparing ') + localStorage.reportValue)
        @$el.find('.submit').addClass('disabled').parent().attr('title', t('Preparing ') + localStorage.reportValue)
        @$el.find('.reportType .drop-down').addClass('disabled') and @$el.find('.reportType .selector').addClass('block') if @reportCategory == 'industryCompliance' or @reportCategory == 'custom'
        @rotate '.bar'

      generateReport:()->
        if localStorage.getItem('reportType')
          @reportType = localStorage.getItem('reportType')
          @reportValue = localStorage.getItem('reportValue')
          @reportCategory = localStorage.getItem('reportCategory')
        localStorage.setItem('reportType',@reportType)
        localStorage.setItem('reportValue',@reportValue)
        localStorage.setItem('reportCategory',@reportCategory)
        @industryComplianceReportsModel = new facade.models.reportGenerator.IndustryComplianceReports([],
          {
            domainId: facade.context.get('href').split('/')[0],
            snapshotId: facade.context.get('snapshot').get('href').split('/')[4],
            templateId: @reportType
          })
        @industryComplianceReportsModel.getData().always((jqXHR)=>
          if jqXHR.status == 202
            localStorage.setItem('reportGenerating', true)
            @showLoader()
            @intervalId = setTimeout(@generateReport.bind(@), 10000)
          else
            $('.loader').hide()
            $('.submit').removeClass('disabled').parent().removeAttr('title')
            localStorage.setItem('reportGenerating', false)
            $('.reportType .drop-down').removeClass('disabled') and @$el.find('.reportType .selector').removeClass('block')
            localStorage.removeItem('reportType')
            localStorage.removeItem('reportValue')
            localStorage.removeItem('reportCategory')
            clearTimeout(@intervalId)
            @notificationMessage(jqXHR)
            window.open(@industryComplianceReportsModel.url(), "_self") if jqXHR.status == 200
          )

      render:() ->
        @$el.html(@template())
        @$el.find('.reportData').html(@reportTemplate({data: true}))
        reportCategories = _.map(facade.portal.get('configuration').reportCategory,(category) -> return {templateLabel:category.label, templateId:category.id})
        @reportCategory = localStorage.getItem('reportCategory')
        reportSelector = @fetchData(reportCategories)
        _.filter(reportSelector.options.data ,(reportData)=>
          @reportCategory = reportData.value if @reportCategory == undefined or @reportCategory == null
          if reportData.value == @reportCategory
            reportData.selected = true)
        $appSelector = @$el.find('#reportCategory')
        $appSelector.html(reportSelector.render())
        @$el.find('.download-file').addClass('disabled')
        @$el.find('#reportCategory .cont .options').attr('data-before', t('Select a report category'))
        @$el.find('.reportCategory.dataSelector ul li:last').addClass('inactive') if facade.portal.get('configuration').reportCategory[2].reportTemplates.length == 0
        @fetchReportType(false)
        reportSelector.on('selection', (data)=>
          return if data == @templates.id
          if data == "industryCompliance" or data == "custom" then generateReport = true else generateReport = false
          @$el.find('.reportData').html(@reportTemplate({data: generateReport}))
          if localStorage.reportGenerating =='true' then @showLoader() else $('.loader').hide()
          @reportCategory = data
          @fetchReportType(true)
        )
    })

    module = {
      initialize: (options) ->
        @options = _.extend({}, options)
        facade.bus.emit('menu:add-item',{
          "className": "report-generator",
          "text": t('Reports'),
          "route": "report",
        })
        facade.bus.on('show', @control ,@)
        facade.bus.on('show', @processBreadcrumb, @)

      control:(options) ->
        return unless 'reportGenerator' == options?.pageId
        if @view?
          @view.remove()
          delete @view

        $(@options.el).html('<div id="report-generator-holder"></div>')
        @view = new ReportGeneratorView({el:'#report-generator-holder'})
        @view.$el.show()
        @view.render()

      processBreadcrumb:(parameters)->
        return unless 'reportGenerator' == parameters.pageId
        facade.bus.emit('theme', {theme:'report-generator'})
        path =[{
          name:t('Reports')
          type: ''
          href: null
          className: ''
        }]
        facade.bus.emit('breadcrumb', {
          pageId:parameters.pageId
          path :path
        })
        facade.bus.emit('header', {criticalFilter:'disable'})
      destroy: () ->
        @view.remove()
    }
    return module

  return ReportGeneratorModule