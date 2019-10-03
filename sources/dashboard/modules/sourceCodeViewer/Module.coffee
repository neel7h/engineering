###
  Defines the rendering of a source code views.
###
SourceCodeModule = (facade) ->
  _ = facade._
  t = facade.i18n.t
  Handlebars = facade.Handlebars

  models = facade.models.sourceCodes
  CodeFragmentViewer = CodeFragmentViewer(facade, models)
  ObjectInViolationViewer = ObjectInViolationViewer(facade, CodeFragmentViewer)
  CyclicalCallViolationViewer = CyclicalCallViolationViewer(facade)
  ViolationBookmarksViewer = ViolationBookmarksViewer(facade, ObjectInViolationViewer, CodeFragmentViewer)
  ViolationPathViewer = ViolationPathViewer(facade, CodeFragmentViewer, models)
  CopyPasteFindingsView = CopyPasteFindingsView(facade)
  NoSourceCodeViewer = NoSourceCodeViewer(facade, models)

  UnavailableView = facade.backbone.View.extend({
    template: Handlebars.compile('<div class="investigation-not-available">
          <h1>{{t "Content not available in past snapshot"}}</h1>
          <p>{{t "Source code data, if available at all, is not available for past snapshots."}}</p>
          <p>{{t "You may only be able to investigate this data in the latest snapshot."}}</p>
          <p>{{t "For security reasons, depending on analysis configuration, source code may not be available at all, even in latest analysis."}}</p>
      </div>')
    render:()->
      @$el.html(@template)
  })

  module = {
    models: models

    initialize: ->
      facade.bus.on('render:sourceCode', @renderSourceCode, this)
      facade.bus.on('render:copyPasteFindings', @renderCopyPastedFindings, this)

    skipIfPastSnapshot:(parameters)->
      return false if facade.context.get('snapshot').isLatest()
      parameters.$el.html(new UnavailableView().render())
      return true

    renderCopyPastedFindings:(parameters)->
      return unless parameters?.$el?
      return if @skipIfPastSnapshot(parameters)
      parameters.$el.html('')
      facade.ui.spinner(parameters.$el)
      snapshotId = facade.context.get('snapshot').getId()
      violationDetails = new models.ViolationDetails({
        ruleId: parameters.rule
        snapshotId: snapshotId
        componentId: parameters.ruleComponent
      })
      $.when(violationDetails.getData()).done(()->
        copyPastefindingsView = new CopyPasteFindingsView(_.extend({}, parameters,{
          violationDetails:violationDetails
          snapshotId:snapshotId
        }))
        parameters.$el?.html(copyPastefindingsView.render())
      )

    renderSourceCode: (parameters)->
      return unless parameters?.$el?
      return if @skipIfPastSnapshot(parameters)
      snapshotId = facade.context.get('snapshot').getId()
      violationDetails = new models.ViolationDetails({
        ruleId: parameters.rule
        snapshotId: snapshotId
        componentId: parameters.ruleComponent
      })
      objectSourceCodes = new models.SourceCodes([], {
        componentId: parameters.ruleComponent
        snapshotId: snapshotId
      })
      parameters.$el.html('')
      facade.ui.spinner(parameters.$el)
      $.when(violationDetails.getData(), objectSourceCodes.getData()).done(()->
        switch violationDetails.getType()
          when 'violationBookmarks'
            sourceCodeView = new ViolationBookmarksViewer(_.extend({}, parameters, {
              violationDetails:violationDetails
              sourceCodes:objectSourceCodes
              pagination:5
            }))
          when 'path'
            sourceCodeView = new ViolationPathViewer(_.extend({}, parameters, {
              violationDetails:violationDetails
              pagination:1
            }))
          when 'object'
            # TODO this criteria to decide to display packages cycles is not specific enough, other rules may be impacted
            if objectSourceCodes.length == 0
              sourceCodeView = new CyclicalCallViolationViewer(_.extend({},{
                violationDetails:violationDetails
              }))
        sourceCodeView = new ObjectInViolationViewer(_.extend({}, parameters, {
          violationDetails:violationDetails
          sourceCodes:objectSourceCodes
        })) unless sourceCodeView?
        parameters.$el?.html(sourceCodeView.render())
      ).fail(()->
        noSourceCodeView = new NoSourceCodeViewer()
        parameters.$el?.html(noSourceCodeView.render())
        )
  }
  return module

# FIXME for test purpose ? boooohhooooh !!
# AMD support (use in require)
if define?.amd?
  define([], () ->
    return SourceCodeModule
  )
# direct browser integration (src include)
else if window?
  window.cast = window.cast or {}
  window.cast.stemModules = window.cast.stemModules or {}
  window.cast.stemModules.sourceCodeModule = SourceCodeModule
