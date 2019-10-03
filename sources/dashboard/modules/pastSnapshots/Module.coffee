###
  Defines the license component.
###
define [],->
  LicenseModule = (facade) ->
    _ = facade._

    PastSnapshotMessage = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<div class="past-snapshot-information">
          <p><em>{{t "Welcome in the past !"}} </em><a href="{{href}}">{{t "Go to latest analysis"}}</a></p>
          <p>{{t "You are currently investigating a past snapshot."}}
          {{t "All data from the past are not available, hence, please consider that your investigation experience will be limited."}}</p>

      </div>')

      events:
        'click a':'follow'

      follow:()->
        window.location = @getUrl()
        window.location.reload(true)

      getUrl:()->
        return '#' + facade.context.get('application').get('href') + '/snapshots/' + facade.context.get('snapshots').getLatest().getId()

      render:()->
        resetHref =
        @$el.html(@template({
          href:@getUrl()
        }))
        return @$el
    })

    # Removing past snapshot header bar :
    # module = {
    #   initialize:(options) ->
    #     @options = facade._.extend({},options)
    #
    #     snapshot = facade.context.get('snapshot')
    #     unless snapshot.isLatest()
    #       @view = new PastSnapshotMessage({
    #         el: @options.el
    #       })
    #       @view.$el.parents().addClass('aed-in-past')
    #       @view.render()
    #
    #   destroy:()->
    #     @view.remove()
    # }
    # return module

  return LicenseModule
