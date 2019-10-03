CopyPasteFindingsView = (facade)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span class="component">
    <em class="short-content" title="{{value}}">{{ellipsisMiddle value 15 35}}</em>
    <em class="large-content" title="{{value}}">{{ellipsisMiddle value 25 45}}</em>
    <em class="super-large-content" title="{{value}}">{{value}}</em>
  </span><a class="view-file-icon" title="{{t "View the violation details located in the file in a separate window."}}"></a>')


  Viewer = backbone.View.extend({
    className: 'code-viewer object-viewer'
    template: Handlebars.compile(' <div class="metric-page" id="component-findings">
          <div class="content-header">
            <h2>{{t "Violation details"}}</h2>
            <p>{{t "This table list the objects having a high similarity with violating object selected."}}</p>
          </div>
          <div id="table-holder" class="component-findings"></div>
          <div class="source-code-fragment-details">
             <h4>{{t "Why is that an issue?"}}</h4>
             <pre>{{violationDetails.rule.rationale}}</pre>
             <button class="learn-more">{{t "Learn more"}}</button>
          </div>')

    events:
      'click .learn-more': 'showDocumentation'

    initialize:(options)->
      @options = _.extend({}, options)
      @violationDetails = options.violationDetails
      @model = new facade.models.sourceCodes.DiagnosisFindings({
          componentId: @options.ruleComponent
          ruleId: @options.rule
          snapshotId: @options.snapshotId
      })

    showDocumentation: ()->
      facade.bus.emit('leave:zoom')
      facade.bus.emit('display:documentation')

    render:()->
      @$el.html(@template({violationDetails:@violationDetails.toJSON()}))
      @model.fetch().done(()=>
        data = @model.asRows()
        @table = new facade.bootstrap.Table({
          columns:[
            {header:t('Object Name Location'), title:t('Object Name Location'), align:'left',format: (value)->
              return _objectNameTemplate({value:value})
            }
          ],
          rows:data
          click:true
        })
        @$el.find('#table-holder').html(@table.render())
        @table.$el.addClass('contract compact')
        @table.on('row:clicked', @onTableSelection, @)

      )
      setTimeout (->
          $(window).resize()
      ), 100
      return @$el

    onTableSelection:(item)->
      return unless item?.extra?.componentId
      viewSourceCode = '#' + SELECTED_APPLICATION_HREF +  '/snapshots/'+@options.snapshotId + '/qualityRuleId/' + @options.rule + '/master/'+ @options.ruleComponent + '/left/' + @options.ruleComponent + '/right/' + item.extra.componentId
      window.open('sourceCopyPaste.html' + viewSourceCode, '_blank')
  })

  return Viewer
