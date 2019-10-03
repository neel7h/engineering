###
  Defines the application selection component. This is supposed to occur after login when the url does not contain
  information regarding selected application.
###
define [], ->

  ApplicationListingModule = (facade) ->
    models = facade.models
    Handlebars = facade.Handlebars
    $ = facade.$
    _ = facade._
    t = facade.i18n.t

    UserContext = facade.backbone.Model.extend({
      url:REST_URL + 'user'
    })

    serverContext = facade.backbone.Model.extend({
      url:REST_URL + 'server'
    })

    ApplicationList = facade.backbone.View.extend({
      tagName:'ul'
      noApplicationsMatchingTemplate:Handlebars.compile('<div class="">{{t "No applications were found to match your search."}}</div>')()
      errorTemplate:Handlebars.compile('<div class="error-message">{{t "You cannot access any application."}}</div>')()
      template:facade.Handlebars.compile('{{#each applications}}
                    <li><a class="application-to-select" data-href="{{href}}">{{name}}</a></li>
                   {{/each}}')

      events:
        'click .application-to-select':'loadPage'

      initialize:(options)->
        @totalApplicationCount = options.totalApplicationCount
        @collection = options.collection

      loadPage:(event)->
        @_loadPage($(event.target).attr('data-href'))

      _loadPage:(locationFragment)->
        application = @collection.findWhere({href:locationFragment})
        return unless application?
        snapshots = new facade.models.snapshots.Snapshots({href:application.get('href') + '/snapshots'})
        snapshots.getData({
          success:()->
            snapshot = snapshots.getLatest()
            window.location = '#' + locationFragment + '/snapshots/' + snapshot.getId()
            window.location.reload(true);
          error:()->
            console.error arguments
        })

      renderList:(applications)->
        @$el.html(@template({applications:applications.toJSON()}))

      render:()->
        if @totalApplicationCount == 0
          @$el.html(@errorTemplate)
          return @
        if @collection.length == 0
          @$el.html(@noApplicationsMatchingTemplate)
          return @
        if @collection.length == 1 and @totalApplicationCount == 1
          singleApplication = @collection.at(0)
          return @_loadPage(singleApplication.get('href'))
        @renderList(@collection)
        @
    })

    ApplicationSelectionView = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<div class="login-space">
      <div id="login-title" class="login-title aed">
        <div class="outer"><div class="middle"><div class="inner">
          <div class="title-block-aed"><h1>CAST </br>{{{t "<em><span class=red>Engineering</span> Dashboard</em>"}}}</h1></div>
        </div></div></div>
      </div>
      <div class="application-listing">
        <div class="listing-header">
          <div id="user-menu"></div>
          <h3>{{t "Please select your application"}}</h3>
        </div>
        <div class="listing-filterer">
          <input type="text" placeholder="{{t "Find"}}" id="application-filter" />
        </div>
        <div class="listing-applications" id="application-listing">
        </div>
      </div>
      </div>')

      events:
        'keyup #application-filter': 'filterApplicationListing'

      initialize:(options)->
        @options = _.extend({},options)
        @collection = new models.applications.ApplicationsWithResults([],{domain:@options.domain})
        @user = new UserContext()
        @server = new serverContext()
        @portalConfiguration = new facade.models.configuration.Portal()

      filterApplicationListing:(event)->
        filter = $(event.target).val()
        filteredApplications = new models.applications.ApplicationsWithResults(@collection.filter((item)->
          item.get('name').toLowerCase().indexOf(filter.toLowerCase()) >= 0
        ),{domain:@options.domain})
        @applications = new ApplicationList({collection:filteredApplications, totalApplicationCount:@collection.length})
        @$el.find('#application-listing').html(@applications.render().$el)

      render:()->
        @$el.hide()
        @$el.html(@template())
        $.when(@server.fetch(),@user.fetch(),@portalConfiguration.fetch()).then(()=>
          facade.bus.emit('setCurrentTime')
          if @portalConfiguration.get('configuration').alertTimeoutInterval then localStorage.setItem('alertTimeoutInterval', @portalConfiguration.get('configuration').alertTimeoutInterval) else localStorage.setItem('alertTimeoutInterval', 10)
          facade.bus.emit('startSession', {that: @,facade: facade, serverData: @server})
          @menu = new facade.bootstrap.Menu({
            text: @user.get('name') or t('Unknown user')
            class: 'light-grey'
            items: [{text: t('Logout'), class: "logout", action: ()->
                facade.bus.emit('logout')
              },
              {text: t('Configuration'), class: "configuration", action:()->
                facade.bus.emit('require:adminPage')
#                window.open('sources/dashboard/reactModules/adminPage/admin.html')
              }]
          });
          @menu.options.items.pop() if !@user.get('administrator')
          @$el.find('#user-menu').html(@menu.render())
          @$el.find('#user-menu .cont .options').attr('data-before',t('Preferences'))
          disableLogout =  false
          disableLogout = true if @server.get('securityMode') == 'saml' and !@server.get('samlSingleLogout')
          if disableLogout
            @$el.find('#user-menu .selector a').hide()
            @$el.find('#user-menu .selector').prop('disabled',true).addClass('disabled')
        )

        show = () -> # to avoid flashing effect
          @$el.show()
          facade.bus.off('login:successful', show)
        facade.bus.on('login:successful', show, @)

        that = @
        @collection.getData({
          success:()=>
            that.applications = new ApplicationList({
              collection:that.collection
              totalApplicationCount:that.collection.length
            })
            if window.location.hash?.split('/')[1] and window.location.hash.indexOf("#applications") != -1
              application = that.collection.findWhere({'name': decodeURI(window.location.hash.split('/')[1])})
              if application
                that.applications._loadPage(application.get('href'))
              else
                window.location.href=' '
            else
              @$el.show()
              @$el.find('#application-listing').html(that.applications.render().$el)
          error:(e)->
            that.applications = new ApplicationList({
              collection:that.collection
              totalApplicationCount:0
            })
            @$el.find('#application-listing').html(that.applications.render().$el)
            console.error('failed trying to reload quality rule with violations view', e)
        })

    })

    module = {
      initialize: (options) ->
        @applicationSelection = new ApplicationSelectionView(options)
        @applicationSelection.render()

      destroy: () ->
        @applicationSelection.remove()
    }
    return module

  return ApplicationListingModule
