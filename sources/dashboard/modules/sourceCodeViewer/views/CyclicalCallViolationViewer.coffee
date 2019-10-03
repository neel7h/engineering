CyclicalCallViolationViewer = (facade)->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  Viewer = backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'
    template: Handlebars.compile('<h2>{{t "Violation details"}}</h2>
      <div class="source-code-fragment-group {{#if isCritical}}critical{{/if}}">
        <p>{{t "The page is displaying the objects associated to the selected object in violation for rule."}}</p>
        <div class="rule-name">{{violationDetails.rule.name}}</div>
        <div class="cyclical-call-details">
          <h3>{{cyclicalCallFindings.name}}</h3><hr/>
          {{#each cyclicalCallFindings.values}}<p>{{this.component.name}}</p>{{/each}}
        </div>
      </div>
      <div class="source-code-fragment-details">
         <h4>{{t "Why is that an issue?"}}</h4>
         <pre>{{violationDetails.rule.rationale}}</pre>
         <button class="learn-more">{{t "Learn more"}}</button>
      </div>')
    objectTemplate: Handlebars.compile('<p>{{component.name}}</p>')

    events:
      'click .learn-more': 'showDocumentation'

    initialize: (options)->
      @violationDetails = options.violationDetails

    showDocumentation: ()->
      facade.bus.emit('leave:zoom')
      facade.bus.emit('display:documentation')

    render: ()->
      @$el.html(@template({
        violationDetails: @violationDetails.toJSON()
        cyclicalCallFindings: @violationDetails.getFindings()
        isCritical: @violationDetails.isCritical()
      }))
      return @$el
  })

  return Viewer
