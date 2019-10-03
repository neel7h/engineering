###
  Define the error display page
###
define [], ->

  errorPageModule = (facade)->

    backbone = facade.backbone
    Handlebars = facade.Handlebars
    _ = facade._

    ErrorPageView = facade.backbone.View.extend({
      template:Handlebars.compile('<div class="error-page"><h1>{{t "Engineering Dashboard"}}</h1>
        <p>{{t "Your application failed to start due to a possible issue:"}} "{{errorType}}"</p>
        <p>{{errorMessage}}</p>
        {{#if jsonError}}<div class="json-area">
            <h3>{{t "Symptoms on file:"}} {{filename}}</h3>
            <p>{{jsonError}}</p>
        </div>{{/if}}
       <div><a href="" class="redirect-link">{{t "Jump to homepage"}}</a></div></div>')

      initialize:(options)->
        @options = _.extend({},options)

      render:() ->
        @$el.html(@template(@options))

    })

    module = {
      initialize:(options)->
        @view = new ErrorPageView(options)
        @view.render()
      destroy:()->
        @view.remove()
    }
    return module

  return errorPageModule
