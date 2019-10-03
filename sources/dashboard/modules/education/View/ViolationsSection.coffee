ViolationsSection = (facade) ->
  Handlebars = facade.Handlebars
  _ = facade._
  Backbone = facade.backbone
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span>
    <em class="short-content" ({{value}})">{{ellipsisMiddle value 40 60}}</em>
    <em class="large-content" ({{value}})">{{ellipsisMiddle value 50 70}}</em>
    <em class="super-large-content" ({{value}})">{{value}}</em>
  </span>')

  _violationsTemplate = Handlebars.compile('<span>
         {{#if href}}
          <em class="short-content" title="{{title}}"><a class="{{state}}" href="{{href}}">&#xe91a;</a></em>
         {{else}}
          <em class="short-content" title="{{title}}"><a class="{{state}}">&#xe91a;</a></em>
         {{/if}}
         </span>')

  ViolationSectionView = Backbone.View.extend({
    template:Handlebars.compile('<div class="violations-overview" id="violations-overview">
            <div class="education-selector"><span>{{t "List of violations in current snapshot"}}</span></div>
            <div class="violations-summary">
              <div class="summary-issues removed-issues" title="{{t "removed"}}">
                <span class="removed-issues-count"></span>
              </div>
              <div class="summary-issues added-violations" title="{{t "added"}}">
                <span class="added-issues-count"></span>
              </div>
            </div>
            <a title="{{t "Download data as excel file"}}" class="download-file snapshot-violations pos disabled">{{t "Download Excel"}}</a>
            <article>
              <div class="violations-issues-listing"></div>
            </article>
              </div>')

    loadingTemplate: '<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    events:
      'click .snapshot-violations': 'downloadViolationsAsExcelFile'

    preRender:()->
      @$el.find('.violations-issues-listing').html(@loadingTemplate)

    initialize:(options)->
      @options = _.extend({},options)
      @businessCriterion = "60017"
      @educatedRules = options.educatedRules
      @ruleIds = _.map(_.filter(@educatedRules.models, (rule) ->return rule if rule.get('active') == false), (rules)-> return rules.get('rulePattern').href.split('/')[2])
      @addedRemovedViolationsModel = new facade.models.violations.AddedRemovedViolations([], {
        ruleIds: @ruleIds,
        href: facade.context.get('snapshot').get('href'),
      })
      @ViolationCount = new facade.models.education.EducationViolationsCount([], {
        ruleIds: @ruleIds,
        href: facade.context.get('snapshot').get('href')
      })
      @qualityAutomationManager = facade.context.get('user').get('qualityAutomationManager')

    downloadViolationsAsExcelFile:()->
      href = @violationsDownloadLink
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
        window.location = href if href?
      )
      return false

    addedRemovedViolations:(callback)->
      @addedRemovedViolationsModel.getData({
        success: ()=>
          that = @
          rows = @addedRemovedViolationsModel.asRows()
          @ViolationCount.getData({
            success: (data)=>
              @count = @ViolationCount.addedRemovedViolationsCount(data)
              columns = [
                {header: t('Rule'), title:t('Rule'),align:'left stretch'},
                {header: t('Object name location'), title:t('Object name location'),align:'left stretch', format: (value)->
                  return _objectNameTemplate({value})
                },
                {header: t('status'), headerMin:'#xe61a;',title:t('Status'), align: 'center', length:4, format: (value)->
                  if value == 'added'
                    return '<span class="status added-violation"></span>'
                  else
                    return '<span class="status removed"></span>'
                },
                {header: t(''), align:'center', format: (value, group, row, model)->
                  title = t('Access the violation source code')
                  state = 'showViolation'
                  href = '#'+ SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' + that.businessCriterion + '/all/' + value + '/' + '_ap'
                  if model.columns[2] != 'added'
                    title = t('The violation is not visible anymore')
                    state = 'hideViolation'
                    href = ''
                  return  _violationsTemplate({href: href, title: title, state:state})
                }
              ]
              @violationsTable = new facade.bootstrap.Table({
                columns: columns
                rows : rows
                rowSelector: false
              })
              callback()
          })
      })

    sortColumn:() ->
      el = @$el
      if @count.addedViolationsCount + @count.removedViolationsCount == 0
        el.find('.violations-issues-listing table tbody').append('<div class="no-rules">' + t('No Violations found') + '</div>')
      el.find('.table .status.removed').attr('summary-data',t('Removed'))
      el.find('.table .status.added-violation').attr('summary-data',t('added'))

    render:() ->
      el = @$el
      el.append(@template())
      @preRender()
      @violationsDownloadLink = @addedRemovedViolationsModel.url()+ '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      @addedRemovedViolations(() =>
        el.find('.added-violations').attr('summary-data',t('added'))
        el.find('.removed-issues').attr('summary-data',t('removed'))
        el.find('.violations-issues-listing').append(@violationsTable.render())
        @$el.find('.violations-issues-listing .loading').remove()
        @$el.find('.download-file').removeClass('disabled')
        if @count.addedViolationsCount + @count.removedViolationsCount == 0
          el.find('.violations-issues-listing table tbody').append('<div class="no-rules">' + t('No Violations found') + '</div>')
          @$el.find('.snapshot-violations').addClass('disabled')
        el.find('.table .status.added-violation').attr('summary-data',t('added'))
        el.find('.table .status.removed').attr('summary-data',t('Removed'))
        el.find('.removed-issues-count').html(@count.removedViolationsCount)
        el.find('.added-issues-count').html(@count.addedViolationsCount)
        el.find('.violations-issues-listing table thead tr:first th.center:last').addClass('violation-header-size')
        @violationsTable.on('sorted', @sortColumn, @)
      )
  })
  return ViolationSectionView
