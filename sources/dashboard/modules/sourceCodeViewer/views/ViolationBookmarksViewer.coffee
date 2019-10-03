ViolationBookmarksViewer = (facade, ObjectInViolationViewer, CodeFragmentViewer) ->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._


  DefectView = backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'

    objectTemplate: Handlebars.compile('<h3>{{t "Defect"}} #{{defectCount}}</h3>
        <hr />
        <div class="source-code-fragment-details">
          <div class="fragment-interaction">
            <!--<button class="view-code-fragment">{{t "View File"}}</button>-->
          </div>
          <div class="source-code-fragment-container"></div>
          <button class="more-bookmarks">{{t "More bookmarks"}}</button>
        </div>')

    events:
      'click .more-bookmarks': 'showMoreBookmarks'

    initialize:(options)->
      @sourceCodes = options.sourceCodes
      @defectCount = options.defectCount
      @violationDetails = options.violationDetails
      @defectBookmarks = options.defectBookmarks
      @pagination = options.pagination || 5
      @startBookmark = 0

    showMoreBookmarks:()->
      @startBookmark = @startBookmark + @pagination
      @_render()

    _render:()->
      for i in [@startBookmark...Math.min(@startBookmark+@pagination,@defectBookmarks.length)]
        isSecondaryBookmark = false
        isSecondaryBookmark= true if i != 0
        codeFragment = @defectBookmarks[i].codeFragment
        codeViewer = new CodeFragmentViewer({
          href: codeFragment.file.href
          name: codeFragment.file.name
          startLine: codeFragment .startLine
          startColumn: codeFragment .startColumn
          endLine: codeFragment .endLine
          endColumn: codeFragment .endColumn
          highlightBookmark: true
          fetchAllBookmark:true
          spread:10
          secondary: isSecondaryBookmark
          componentId:this.sourceCodes.componentId
          currentSnapshotHref:facade.context.get('snapshot').get('href')
        })
        @$el.find('.source-code-fragment-container').append(codeViewer.render())


        if @defectBookmarks.length > @startBookmark + @pagination
          @$el.find('.more-bookmarks').show()
        else
          @$el.find('.more-bookmarks').hide()

    render:()->
      @$el.html(@objectTemplate({
        defectCount:@defectCount
        violationDetails: @violationDetails
      }))

      @_render()
      return @$el
  })

  Viewer = backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'

    template: Handlebars.compile('<h2 class="source-code">{{t "Source code"}}</h2>
      <div class="source-code-fragment-group {{#if isCritical}}critical{{/if}}">
        <p> {{totalDefectsNum}} {{t "defect(s) have been found on this violation, "}} <span class="defects-count"></span> {{t "defect(s) loaded"}}</p>
        <p class="code-fragment-status">{{t "Code"}} {{assign this "code"}} {{t "and violation" }} {{assign this "violation"}} {{t "since the last snapshot analysis"}}</p>
        <div class="rule-name">{{violationDetails.rule.name}}</div>
      </div>
      <div class="show-more-defects">
        <button class="show-more">{{t "More defects"}}</button>
      </div>
      <div class="source-code-fragment-details">
      <h4 class="violation-details">{{t "Violation details"}}</h4>
      {{#if callFindings.values.length}}
        <div class="source-code-fragment-group-violation {{#if isCritical}}critical{{/if}}">
          <p>{{t "The page is displaying the objects associated to the selected object in violation for rule."}}</p>
            <div class="call-details">
              <h3>{{callFindings.name}}</h3><hr/>
              <p>{{#valueType callFindings}} {{/valueType}}</p>
            </div>
      {{else}}
        <p>{{t "No violation details for this Rule"}}</p>
      {{/if}}
       <h4>{{t "Why is that an issue?"}}</h4>
       <pre>{{violationDetails.rule.rationale}}</pre>
         <button class="learn-more">{{t "Learn more"}}</button>
      </div></div>')

    events:
      'click .learn-more': 'showDocumentation'
      'click .show-more': 'showMoreDefects'

    initialize: (options)->
      @sourceCodes = options.sourceCodes
      @violationDetails = options.violationDetails
      @pagination = options.pagination || 5
      @startDefect = 0
      @defectCount =1

    showDocumentation: ()->
      facade.bus.emit('leave:zoom')
      facade.bus.emit('display:documentation')


    showMoreDefects:()->
      @startDefect = @startDefect + @pagination
      @processCodeFragments()

    processCodeFragments:()->
      $defectViewContainer = @$el.find('.source-code-fragment-group')
      violationDetails = @violationDetails.toJSON()
      violationFindings = @violationDetails.getFindings()

      defects = violationFindings.bookmarks
      for i in [@startDefect...Math.min(defects.length,@startDefect + @pagination)]
        defectView = new DefectView({
          sourceCodes:@sourceCodes
          defectCount:@defectCount++
          violationDetails: violationDetails
          defectBookmarks: defects[i]
          pagination: 5
        })
        $defectViewContainer.append(defectView.render())

      $defectCount = $('<em>'+@defectCount+'</em>')
      @$el.find('.defects-count').html(@defectCount-1)
      if defects.length > @startDefect + @pagination
        @$el.find('button.show-more').show()
      else
        @$el.find('button.show-more').hide()

    render: ()->
      @$el.html(@template({
        violationDetails: @violationDetails.toJSON()
        isCritical: @violationDetails.isCritical()
        callFindings: @violationDetails.getFindings()
        totalDefectsNum: @violationDetails.getFindings().bookmarks.length
      }))
      @processCodeFragments()
      return @$el
  })

  return Viewer
