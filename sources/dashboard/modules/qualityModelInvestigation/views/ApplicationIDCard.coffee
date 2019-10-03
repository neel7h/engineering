ApplicationIDCard = (facade)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  apps = facade.models.applications

  Model = backbone.Model.extend({

    getData:(options)->
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      that.application = new apps.Application({href:@get('href')})
      that.application.getData({
        success:(application)->
          that.snapshots = new apps.Snapshots({href:that.application.getSnapshotsURL()})
          that.snapshots.getData(fullOptions)
        error:()->
          alert('error while fetching application')
      })
  })

  return backbone.View.extend({
    className:'card-content'
    template:Handlebars.compile('<section>
            <div class="card-header">
            <h2>{{t "Application"}}</h2>
            <h3>{{t "Risk Model Investigation"}}</h3>
            </div>

            <div class="section-card-content left-section">
              <div class="drill-button"></div>
              <div class="snapshot-information">
                <div class="information"><div class="label"><span>{{t "Snapshots"}}:</span></div><div class="value"><span>{{snapshot.annotation.name}}</span></div></div>
                <div class="information"><div class="label"><span>{{t "Version"}}:</span></div><div class="value"><span>{{snapshot.annotation.version}}</span></div></div>
                <div class="information"><div class="label"><span>{{t "Date"}}:</span></div><div class="value"><span>{{snapshot.annotation.date.isoDate}}</span></div></div>
              </div>
            </div>
            <div class="section-card-content right-section">

            </div>
          </section>
          <footer>
            <div class="section-card-footer left-section"></div>
            <div class="section-card-footer right-section">
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate.</p>
            </div>
          </footer>
    ')

    initialize: ()->
      @model = new Model({href:SELECTED_APPLICATION_HREF})

    render: ()->
      @$el.html(@template({
        application:@model.application.toJSON(),
        snapshot:@model.snapshots.getLatest().toJSON()
      }))
  })
