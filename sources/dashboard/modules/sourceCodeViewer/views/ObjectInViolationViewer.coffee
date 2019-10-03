ObjectInViolationViewer = (facade, CodeFragmentViewer)->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  Viewer = backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'
    template: Handlebars.compile('<h2 class="source-code">{{t "Source code"}}</h2>
      <div class="source-code-fragment-group {{#if isCritical}}critical{{/if}}">
        <p class="code-fragment-status">{{t  "Code"}} {{assign this "code"}} {{t "and violation" }} {{assign this "violation"}} {{t "since the last snapshot analysis"}} </p>
        <div class="rule-name">{{violationDetails.rule.name}}</div>
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
        <p>{{t "No violation details for this rule"}}</p>
      {{/if}}
      <h4>{{t "Why is that an issue?"}}</h4>
      <pre>{{violationDetails.rule.rationale}}</pre>
         <button class="learn-more">{{t "Learn more"}}</button>
      </div></div>')
    objectTemplate: Handlebars.compile('<!--<h3>{{sourceCode.file.name}}</h3><hr />-->

        <div class="source-code-fragment-details">
          <div class="fragment-interaction">
          </div>
          <div class="source-code-fragment-container"></div>
        </div>')

    events:
      'click .learn-more': 'showDocumentation'

    initialize: (options)->
      @sourceCodes = options.sourceCodes
      @violationDetails = options.violationDetails
      @pagination = options.pagination

    showDocumentation: ()->
      facade.bus.emit('leave:zoom')
      facade.bus.emit('display:documentation')

    processCodeFragments: ($objects)->
      @$el.find('h2.source-code').after(Handlebars.compile('<p>{{t "No violation bookmarks or details are available on this violation, object source code will be displayed instead when applicable."}}</p>')())
      violationDetails = @violationDetails.toJSON()
      @sourceCodes.each((sourceCode)=>
        $object = $(@objectTemplate({
          sourceCode: sourceCode.toJSON()
          violationDetails: violationDetails
        }))
        codeViewer = new CodeFragmentViewer({
          href: sourceCode.get('file').href
          name: sourceCode.get('file').name
          startLine: sourceCode.get('startLine')
          startColumn: sourceCode.get('startColumn')
          endLine: sourceCode.get('endLine')
          endColumn: sourceCode.get('endColumn')
          highlightBookmark: false
          componentId:this.sourceCodes.componentId
          currentSnapshotHref:facade.context.get('snapshot').get('href')
        })
        $object.find('.source-code-fragment-container').html(codeViewer.render())
        $objects.append($object)
      )

    render: ()->
      @$el.html(@template({
        violationDetails: @violationDetails.toJSON()
        callFindings: @violationDetails.getFindings()
        isCritical: @violationDetails.isCritical()
      }))
      @processCodeFragments(@$el.find('.source-code-fragment-group'))
      return @$el
  })

  return Viewer
