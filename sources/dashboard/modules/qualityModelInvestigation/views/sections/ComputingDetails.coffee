ComputingDetailsSection = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  _ = facade._
  t = facade.i18n.t

  ComputingDetailCloseVIew = backbone.View.extend({
    className: 'computing-details'
    title: '<span>' + t('Computing details') + '</span>'
    # FIXME do we need 2 templates or a template that handles existence or not of values ?
    _noViolationRatioTemplate: Handlebars.compile('
                            <h2>{{{title}}}</h2>
                            <div>{{t "No computing details yet on measures and distributions"}}</div>
                            <footer></footer>
                      ')
    template: Handlebars.compile('<h2>{{{title}}} <span class="total-checks">{{formatNumber totalChecks "0,000"}}</span> <span class="checks">{{t "Total checks"}}</span></h2>
                            {{#if nModule}}<div><em>{{nModule}}</em> {{t "checked module(s) out of"}} <em>{{totalModules}}</em></div>{{/if}}
                            <div><span class="{{complianceLevel}}"></span><em>{{ratio}}</em> {{t "Compliancy"}}</div>
                            <footer></footer>
                      ')

    initialize: (options)->
      @updateModel(options)

    formatRatio:(value)->
      return numeral(value).format('0%') if (value * 10000) % 100 == 0
      return numeral(value).format('0.0%') if (value * 10000) % 10 == 0
      return numeral(value).format('0.00%')

    identifyComplianceLevel:(value)->
      return 'compliance-good-close' if value > 0.9
      return 'compliance-warn-close'


    updateModel: (options)->
      @model = new facade.models.QualityRuleComputingDetail({
        applicationHref: window.SELECTED_APPLICATION_HREF
        snapshotId: facade.context.get('snapshot').getId()
        qualityRuleId: options.rule
        moduleHref:facade.context.get('module')?.get('href')
        technology:facade.context.get('technologies').getSelectedEncoded()
      })

    updateViewState:(parameters)->
      @$el.html(@template({title: @title}))
      facade.ui.spinner(@$el)
      @updateModel(parameters)
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload computing details closed view', e)
      })
      return

    render: ()->
      if facade.context.get('module')?
        moduleResult = @model.getModuleResult()
        result = moduleResult?.result
      else
        applicationResult = @model.getApplicationResult()
        result = applicationResult?.result
      if result?.violationRatio?
        nModuleResults = applicationResult?.moduleResults.length
        @$el.html(@template({
          title: @title,
          totalChecks: result.violationRatio.totalChecks,
          nModule:nModuleResults,
          ratio:@formatRatio(result.violationRatio.ratio),
          complianceLevel:@identifyComplianceLevel(result.violationRatio.ratio),
          totalModules:@model._modules.length}

        ))
      else
        @$el.html(@_noViolationRatioTemplate({title: @title}))

  })

  ComputingDetailSectionVIew = backbone.View.extend({
    className: 'computing-details'
    title: t('Computing details')
    template: Handlebars.compile('
                        <div class="detail-header">
                            <div class="close-section"></div>
                            <h2>{{title}}</h2>
                        </div>
                        <div id="table-holder" class="table-computing"></div>
                        <footer></footer>
                  ')
    _noViolationRatioTemplate: Handlebars.compile('<div>{{t "No computing details yet on measures and distributions"}}</div>')
    _moduleTemplate: Handlebars.compile('<span title="{{this}}">{{ellipsis this 35}}</span>')

    initialize: (options)->
      @updateModel(options)

    updateModel: (options)->
      @model = new facade.models.QualityRuleComputingDetail({
        applicationHref: window.SELECTED_APPLICATION_HREF
        snapshotId: facade.context.get('snapshot').getId()
        qualityRuleId: options.rule
        technology:facade.context.get('technologies').getSelectedEncoded()
      })

    updateViewState:(parameters)->
      @$el.html(@template({title: @title}))
      facade.ui.spinner(@$el)
      @updateModel(parameters)
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload computing details view', e)
      })
      return

    render: ()->
      @$el.html(@template({title: @title}))
      that = @
      applicationResult = @model.getApplicationResult()
      result = applicationResult?.result
      if result?.violationRatio?
        rows = @model.asRows({moduleFilter:facade.context.get('module')?.getSnapshotsHREF()})
        table = new facade.bootstrap.Table({
          columns:[
              {header:t('module'), title:t('Module Name'), length: 4,format:(value)->
                return that._moduleTemplate(value)
              }
              {header: t('total check'), headerMin:'#xe619;', title:t('Total Check Number'), align:'right', length: 4, format: (value)->
                return '<span>n/a</span>' if value < 0
                return '<span>' + numeral(value).format('0,000') + '</span>'
              }
              {header: t('viol.'), headerMin:'#xe618;', title:t('Number Of Violations'), align:'right', length: 4, format: (value)->
                return '<span>n/a</span>' if value < 0
                return '<span>' + numeral(value).format('0,000') + '</span>'
              }
              {header: t('compliance'), headerMin:'#xe617;', title:t('Compliance Percentage'), align:'right', headerMin: '#xe611;', length: 4, format: (value)->
                return '<span>n/a</span>' if value < 0
                if (value * 10000) % 100 == 0
                  formatValue = numeral(value).format('0%')
                else if (value * 10000) % 10 == 0
                  formatValue = numeral(value).format('0.0%')
                else
                  formatValue = numeral(value).format('0.00%')
                return '<span class="compliance-good">' + formatValue + '</span>' if value > 0.9
                return '<span class="compliance-warn">' + formatValue + '</span>'
              }
          ],
          rows:rows
        })
        @$el.find('#table-holder').html(table.render())
      else
        @$el.find('#table-holder').html(that._noViolationRatioTemplate())
      @$el
  })

  return {
    ComputingDetailCloseVIew
    ComputingDetailSectionVIew
  }
