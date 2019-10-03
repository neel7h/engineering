###
  Defines the rendering of a rule documentation.
###
define [], ->

  DocumentationModule = (facade) ->

    backbone = facade.backbone
    Handlebars = facade.Handlebars
    _ = facade._

    DocumentationView = backbone.View.extend({
      className: 'documentation push-footer'
      template: Handlebars.compile('<div class="detail-header"><div class="close-section"></div><h2>{{title}}</h2></div>
                  {{#if model.name}}<div class="rule-name"><label>{{t "Name"}}</label><pre>{{model.name}}</pre></div>{{/if}}
                  {{#if model.rationale}}<div><label>{{t "Rationale"}}</label><pre>{{model.rationale}}</pre></div>{{/if}}
                  {{#if model.description}}<div><label>{{t "Description"}}</label><pre>{{{model.description}}}</pre></div>{{/if}}
                  {{#if model.remediation}}<div><label>{{t "Remediation"}}</label><pre>{{model.remediation}}</pre></div>{{/if}}
                  {{#if model.reference}}<div class="rule-reference"><label>{{t "Reference"}}</label><pre>{{{model.reference}}}</pre></div>{{/if}}
                  {{#if model.sample}}<div><label>{{t "Sample"}}</label><pre>{{model.sample}}</pre></div>{{/if}}
                  {{#if model.remediationSample}}<div><label>{{t "Remediation Sample"}}</label><pre>{{model.remediationSample}}</pre></div>{{/if}}
                  {{#if model.output}}<div><label>{{t "Output"}}</label><pre>{{model.output}}</pre></div>{{/if}}
                  {{#if model.total}}<div><label>{{t "Total"}}</label><pre>{{model.total}}</pre></div>{{/if}}
                  <footer></footer>')

      initialize: (options)->
        @options = _.extend({},options)
        @model = new facade.models.documentationPattern.RulePattern({qualityRuleId: options.rule})

      render:()->
        @$el.html(@template({title: @options.title, model: @model.toJSON()}))
        facade.ui.spinner(@$el)
        @model.getData({
          success:()=>
            @model.attributes.reference = @model.attributes.reference?.replace(/((https?|ftp):\/\/[A-Za-z0-9\/:%_+.,#?!@&=-]+)/g, '<a href="$1" target="_blank">$1</a> ')
            @model.attributes.description = @model.attributes.description?.replace(/((https?|ftp):\/\/[A-Za-z0-9\/:%_+.,#?!@&=-]+)/g, '<a href="$1" target="_blank">$1</a> ')
            @$el.html(@template({title: @options.title, model: @model.toJSON()}))
          error:(e)->
            @$el.html(Handlebars.compile('<h2>{{t "Error occurred while loading documentation"}}</h2>')())
            console.error('failed trying to load documentation view', e)
        })
    })

    DocumentationSummaryView = DocumentationView.extend({
      className:null
      template: Handlebars.compile('<h2>{{title}}</h2>
                  {{#if model.rationale}}<p>{{ellipsis model.rationale 150}}</p>{{else}}<p>{{t "Click to get documentation"}}</p>{{/if}}')
    })

    module = {

      initialize: ->
        facade.bus.on('render:documentation', @renderDocumentation, this)
        facade.bus.on('render:documentation:summary', @renderDocumentationSummary, this)

      renderDocumentationSummary:(parameters)->
        documentationView = new DocumentationSummaryView(parameters)
        documentationView.render()
        parameters.$el?.html(documentationView.$el)


      renderDocumentation:(parameters)->
        documentationView = new DocumentationView(parameters)
        documentationView.render()
        parameters.$el?.html(documentationView.$el)

    }
    return module

  return DocumentationModule
