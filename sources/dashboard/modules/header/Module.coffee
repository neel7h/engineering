###
  Defines the application header components.
###
define [], ->

  HeaderModule = (facade) ->
    t = facade.i18n.t
    Handlebars = facade.Handlebars
    SnapshotPoint = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<h3>{{t "Snapshot"}}</h3><p>{{name}}</p><h3>{{t "Version"}}</h3><p>{{version}}</p><h3>{{t "Date"}}</h3><p>{{date}}</p><button {{#if current}}title="{{t "action is not available on currently selected snapshot"}}" disabled{{/if}}>{{t "Select Snapshot"}}</button>
              <div class="multiple-snapshot-warning">{{t "In case of many snapshots, hold the left mouse button down and select the period you require."}}</div><div class="reload-warning">{{t "Snapshot selection will cause whole application to restart."}}</div>')

      events:
        'click button':'loadSnapshot'

      loadSnapshot:()->
        window.location = '#' + SELECTED_APPLICATION_HREF + '/snapshots/' + @options.data.id
        window.location.reload(true)

      initialize:(options)->
        @options = options

      render:()->
        selectedSnapshot = facade.context.get('snapshot')
        @$el.html(@template(facade._.extend({current:selectedSnapshot.getId() == @options.data.id}, @options.data)))
        return @$el

    })

    SnapshotSelector = facade.backbone.View.extend({
      className:'snapshot-selector'
      template:facade.Handlebars.compile('<div class="snapshot-selector-chart"></div><div class="snapshot-selector-details"></div>
      <p class="snapshot-selector-warning">{{t "Not all data from a previous snapshot is available, therefore some features may be limited in functionality."}}</p>')
      dateTemplate:facade.Handlebars.compile('{{formatDate time "YYYY MMM"}}')

      initialize:(options)->
        snapshots = facade.context.get('snapshots')
        data = {
          values:[]
          snapshots:[]
        }
        @data = data
        selectedSnapshot = facade.context.get('snapshot')
        snapshots.models.forEach((model)->
          data.values.push({
            x:model.get('annotation').date.time
            y:0
            name:model.get('annotation').name
            date:model.get('annotation').date.isoDate
            version:model.get('annotation').version
            selected:model.getId() == selectedSnapshot.getId()
            id:model.getId()
          })
          data.snapshots.push(model.toJSON())
        )
        @data = data

      snapshotSelection:(selection, unselect)->
        if (true == unselect) # means was selected and is deselecting...
          # empty selection
          @$el.find('.snapshot-selector-details').html('<h3>' + t('No snapshot selected') + '</h3>')
        else
          @$el.find('.snapshot-selector-details').html(new SnapshotPoint({data:selection}).render())

      render:()->
        that = @
        @$el.html(@template())
        @$el.find('.snapshot-selector-chart').highcharts({
          title:
            text: null
          tooltip:
            shape: 'square'
            useHTML:true
            borderWidth:0
            positioner: (labelWidth, labelHeight, point) ->
              if point.plotX + labelWidth > this.chart.plotWidth
                tooltipX = Math.abs(point.plotX + this.chart.plotLeft - labelWidth)
              else
                tooltipX = point.plotX + this.chart.plotLeft
              return { x: tooltipX, y: point.plotY + 30 }
          chart:
            height: 200
            width: 360
            type:'line'
          colors: ['#017eff']
          xAxis:
            type:'datetime'
            # labels:
            #   formatter:(value)->
            #     return that.dateTemplate({time:this.value})
          yAxis: {
            labels:
              formatter:(value)-> return ''
            title:
              text: null
            # enabled:false
          },
          plotOptions:
            line:
              events:
                click:(event)->
                  snapshotIndex = event.point.index
                  selection = this.chart.getSelectedPoints()
                  that.snapshotSelection(event.point, event.point.selected)
              allowPointSelect: true
              marker:
                fillColor:'#ffffff'
                lineColor:'#017eff'
                lineWidth:2
                enabled:true
                radius:6
                states:
                  select:
                    fillColor: '#0064cc'
                    lineColor: '#017eff'
                    lineWidth: 2
                    radius: 6
              tooltip:
                pointFormatter:()->
                  return "<div><b>#{t('Version ')}</b>#{this.version}</div><div><b>#{t('Snapshot for ')}</b>#{this.date}</div>"
          legend:
            enabled:false
          series: [{
            name:'Snapshots'
            data: @data.values
          }]
        })
        @snapshotSelection(facade._.findWhere(this.data.values,{selected:true}))
        return @$el

    })

    HeaderView = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<header class="header">
        <div class="application-block">
          <div class="application-info">
            <span><h1 class="large">{{t "Engineering Dashboard"}} - </h1><h1 title="{{t "Engineering Dashboard"}}" class="small">{{t "ED"}} - </h1><div id="application-selector"></div></span>
            <div class="menus">
              <div class="menu-icons">
                <div class= "separator"></div>
                <a class= "search-action">
                  <i class="search-icon">&#xe600;</i><span class="search-title">{{t "search"}}</span>
                </a>
                <div class="notification-box">
                  <a class= "filter-action">
                    {{#if filtering}}
                      <i class="critical-icon"></i>
                      <span class="critical-title active">{{t "only critical"}}<br>{{t "violations"}}</span>
                    {{else}}
                      <i class="non-critical-icon"></i>
                      <span class="critical-title inactive">{{t "only critical"}}<br>{{t "violations"}}</span>
                    {{/if}}
                  </a>
                </div>
                <a class= "export-action">
                  <i class="export-icon"></i><span class="share-title">{{t "share your"}}<br>{{t "screen"}}</span>
                </a>
                <div class= "separator"></div>
                <a class= "snapshot-action">
                  <i class="time-icon{{#if isPastSnapshot}} in-past{{/if}}"></i><span class="snapshot-title">{{t "select a"}}<br>{{t "snapshot"}}</span>
                </a>
              </div>
              <div class="snapshot-info">
                <div class="message">{{t "Snapshot"}}: <b>{{snapshot.name}}</b></div>
                <div class="message-small">{{t "Version"}}: <b>{{snapshot.version}}</b> - {{t "Date"}}: <b>{{snapshot.date.isoDate}}</b></div>
              </div>
            </div>
          </div>
          <div id="search-box" class="search-box"></div>
        </div>
        <div class="user-block">
          <div id="user-menu"></div>
          <div class="user-picture" id="user-picture">&#xe620;</div>
        </div>
      </header>')

      notificationTemplate:facade.Handlebars.compile('<div class="critical-notification">
        <div class="notification-popup align-drop-down">
          <div class="message">
            <span class="remove-notification"></span>
              <h3><span>{{t "Only Critical Violations are displayed by default."}}</span></h3><br/> {{{t "To get all violations, please deactivate &#39;only critical violations&#39;"}}}<br/>{{t "filter icon."}}</div>
        </div>
      </div>')

      events:
        'click .export-action': 'shareDashboard'
        'click .filter-action': 'toggleCriticalFilter'
        'click .search-action': 'clickOnSearch'
        'click .snapshot-action': 'showSnapshotsDialog'
        'click .remove-notification':'terminate'
        'mouseover .filter-action': 'onHover'
        'mouseout .filter-action': 'removeHover'

      popUpCritical:()->
        localStorage.setItem('isCritical', true)
        $('.notification-box').append(@notificationTemplate)
        if @$el.find('.menu-icons .filter-action').hasClass('disabled-selector')
          $('.notification-box .notification-popup').hide()

      onHover:(event)->
        @$el.find('.filter-action i').addClass('activate')
        @$el.find('.critical-title').addClass('activate-title')

      terminate:()->
        $('.critical-notification').remove()

      removeHover:(event)->
        @$el.find('.filter-action i').removeClass('activate')
        @$el.find('.critical-title').removeClass('activate-title')

      enableHeader:(filter)->
        if filter.criticalFilter == 'enable'
          @$el.find('.menu-icons .filter-action').removeClass('disabled-selector')
        else
          @$el.find('.menu-icons .filter-action').addClass('disabled-selector')
          $('.notification-box .notification-popup').hide()

      toggleCriticalFilter:(event)->
        facade.portal.setFilterSetting('criticalsOnly', !facade.portal.userIsFiltering())
        @$el.find('.filter-action i').removeClass('activate')
        @$el.find('.critical-title').removeClass('activate-title')
        @$el.find('.filter-action i').toggleClass('critical-icon non-critical-icon')
        @$el.find('.critical-title').toggleClass('active inactive')
        $('.critical-notification').remove()

      showSnapshotsDialog:(event)->
        snapshotDropDown =  new facade.backbone.DropDownDialogView({
          $attach:this.$el.find('.time-icon')
          title:t('Snapshots selector')
          height:280
          width:500 ## desired width
          isHeader: true
        })
        snapshotDropDown.render()
        snapshotDropDown.addContent(new SnapshotSelector().render())

      shareDashboard: () ->
        UrlModel = Backbone.Model.extend(
          makeUrl: (tags) ->
            urlStr=@get('url')
            urlSep='?'
            for paramKey, paramVal of @get('params')
              paramVal = paramVal.replace( new RegExp('\\$'+tagKey,'g'), tagVal) for tagKey, tagVal of tags
              urlStr+= urlSep + paramKey + '=' + encodeURIComponent(paramVal)
              urlSep="&"
            return urlStr
        )

        UrlCollection = Backbone.Collection.extend(
          url: 'resources/urls.json'
          model: UrlModel

          makeUrl: (mailToId, tags) ->
            return @get(mailToId).makeUrl tags
        )
        urlsStore = new UrlCollection()
        urlsStore.fetch().done(()->
          myUrl = window.location.href
          tags = {urlToShare:myUrl}
          window.location.href = urlsStore.makeUrl("share-dashboard", tags)
        )

      clickOnSearch:()->
        $searchBox = @$el.find('#search-box')
        facade.bus.emit('request:search-dialog',{$el: $searchBox})

        # Detect if CSS animation is available on the browser. If not, just add the last class directly
        if Modernizr.csstransitions
          $searchBox.on 'webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend', (event) ->
            $searchBox.off 'webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend'
            $searchBox.find('.close-wrap').addClass('visible')
            return
        else
          $searchBox.find('.close-wrap').addClass('visible')
        # End of CSS animation fallback
        $searchBox.addClass('open').addClass('above')

      closeSearchBox:(options)->
        options = _.extend({animate:true},options)
        $searchBox = @$el.find('#search-box')
        # Detect if CSS animation is available on the browser. If not, just add the last class directly
        if options.animate and Modernizr.csstransitions
          $searchBox.on 'webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend', (event) ->
            $searchBox.off 'webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend'
            $searchBox.removeClass('above')
        else
          $searchBox.removeClass('above')
        # End of CSS animation fallback
        $searchBox.find('.close-wrap').removeClass('visible')
        $searchBox.removeClass('open')

      initialize:()->
        that = @
        @UserMenuItems = [
          {text: t('Reset homepage'), class: "reset-home-page", value: "reset-home-page", action: (item)->
            localStorage.removeItem('isCritical')
            $('.critical-notification').remove()
            that.popUpCritical()
            facade.bus.emit('data:store:reset', {key:'filters'}) # reset filters first
            facade.bus.emit('data:store:reset', {key:'profiles'})
            $('.filter-action i').addClass('critical-icon').removeClass('non-critical-icon')
            $('.critical-title').addClass('active').removeClass('inactive')
          },
          {text: t('Change Language'), class: "change-language", value: "change-language", action: (item)->
            resetLanguageDialog =  new facade.backbone.DialogView({
              title: t('Change Language')
              subTitle: ''
              message: t('Select a Language')
              language: t('')
              cancel: t('Cancel')
              perform: t('Change')
              theme: 'background-orange'
              action: 'reset'
              content: true
              image: ''
              languageList: JSON.parse(localStorage.getItem('availableLanguages'))
              defaultLanguage: facade.portal.get('configuration').defaultLanguage
              onPerform: (selectedLanguage)->
                localStorage.setItem("language",selectedLanguage)
                window.location = '#' + SELECTED_APPLICATION_HREF
                window.location.reload(true)
            })
            resetLanguageDialog.render()
          },
          {text: '<span>' + t('Logout') + '</span>', class: "logout", value: "logout", action: (item)->
            confirmLogout = facade.portal.get('configuration')?.confirmLogout
            server = facade.context.get('server')
            disableLogout = false
            disableLogout = true  if server.get('securityMode') == 'saml' and  !server.get('samlSingleLogout')
            message = t('Are you sure you want to quit?')
            message = t('Single sign on is enabled. To logout, please close the browser window')  if disableLogout
            if confirmLogout
              logoutDialog =  new facade.backbone.DialogView({
                title:t('Logout')
                subTitle: ''
                message: message
                cancel:t('Cancel')
                perform:t('Logout')
                image: 'logout'
                action: 'logout'
                button: true
                theme: 'background-orange'
                onPerform:()->
                  facade.bus.emit('logout')
              })
              logoutDialog.render()
              logoutDialog.$el.find('#perform').hide() if disableLogout
            else
              facade.bus.emit('logout')
          }
        ]
        facade.bus.on('header', @enableHeader, @)
        facade.bus.on('login:success', @updateLogin, @)
        facade.bus.on('request:close-search',@closeSearchBox,@)
        facade.bus.on('show', @updateSearchTitle, @)
        $(window).on('resize',()=>@resize())

      updateSearchTitle:()->
        if window.location.href.indexOf("componentsInvestigation") > -1
          @$el.find('.search-action').attr('title', t('Objects search'))
        else
          @$el.find('.search-action').attr('title', t('Rules search'))

      updateLogin:(options)->
        @$el.find('#user-menu .selector .label').html(options.userName) if options?.userName?

      resize:()-> # TODO what is it used for ? Is it necessary ?
        userBlockWidth = @$el.find('.user-block').outerWidth(true)
        @$el.find('.application-block').css('right', userBlockWidth)

      renderUserMenu:()->
        @menu = new facade.bootstrap.Menu({
          text: @attributes.userName or "CAST"
          class: 'light-grey right'
          items: @UserMenuItems
        })
        snapshot = facade.context.get('snapshot')
        if snapshot.isLatest()
          @$el.find('.current-snapshot').hide()
        @$el.find('#user-menu').html(@menu.render());

      render:()->
        snapshotInfo = facade.context.get('snapshot');
        userName = @attributes.userName or "CAST"

        @$el.html(@template({
          isPastSnapshot:facade.context.get('snapshots').getLatest().getId() != snapshotInfo.getId()
          snapshot:snapshotInfo.toJSON().annotation,
          username:userName
          filtering:facade.portal.userIsFiltering()
        }))
        @renderUserMenu()
        @popUpCritical() if !localStorage.getItem('isCritical')
        name = ''
        data = [];
        process = (error)=>
          for app in @attributes.applications.toJSON()
            data.push({
              label: app.name
              value: app.href
              selected: app.href == SELECTED_APPLICATION_HREF
            })
          applicationSelector = new facade.bootstrap.Selector({name: name, data: data, class: 'light-grey', maxCharacters:20});
          $appSelector = @$el.find('#application-selector')
          $appSelector.html(applicationSelector.render());
          @$el.find('#application-selector .drop-down').addClass('auto-cursor') if data.length == 1
          @$el.find('#application-selector .drop-down .selector').addClass('disabled').parent().attr('title', data[0].label) if data.length == 1
          if error
            $appSelector.find('.cont').addClass('application-load-error')
          @$el.find('#application-selector .cont .options').attr('data-before', t('Select an application'))
          applicationSelector.on('selection', (item)->
#            localStorage.removeItem("selectedCriteria")
            window.location = '#' + item
            window.location.reload(true);
          )

        @attributes.applications.getData({
          success: () =>
            process()
          error: () =>
            console.error('Error while fetching applications', arguments)
            process(true)
        })


        # FIXME help configuration should be doable from configuration file instead of code itself

        searchHelpviewOptions = {
          $target:@$el.find('#search-box'),
          anchor:'right',
          position:'bottom-left',
          title:t('Search') ,
          content:t('You can search any rule from the Risk Model that has been activated for the selected snapshot in the Homepage or in the Risk investigation view.') + '<br/>' + t('You can search any application object that has been identified for the last snapshot in the Application Investigation view.')
        }
        facade.bus.emit('help:createView',searchHelpviewOptions)

        snapshotHelpviewOptions = {
          $target:@$el.find('.time-icon'),
          anchor:'left',
          position:'bottom-left',
          title:t('Snapshots') ,
          content:t('This option enables you to select a specific snapshot to investigate - if multiple snapshots are available for the current Application.') +
            '<br/>' + t("This allows you to 'go back in time' and investigate data from a previous snapshot.") + '<br/>' + t('Note that not all data is available for previous snapshots.')
        }
        facade.bus.emit('help:createView',snapshotHelpviewOptions)

        applicationNameHelpviewOptions = {
          $target:@$el.find('#application-selector'),
          anchor:'right',
          position:'bottom-right',
          title:t('Application Name') ,
          content:t('You can decide to change the context of your application by selecting another application if you are authorized to see multiple applications.') + '<br/>' + t('Then, when you load a new context of your application, you will loose the previous one')
        }
        facade.bus.emit('help:createView',applicationNameHelpviewOptions)

        homeConfigurationHelpviewOptions = {
          $target:@$el.find('#user-menu .selector .label'),
          anchor:'right',
          position:'bottom-left',
          title:t('Homepage configuration') ,
          content:t('You can re-organize tiles position and resize them also.') + '<br/>' +t("Then if you want to come back to the default homepage configuration, you can click on " )+ '<strong>' + t("'Reset Homepage'") + '</strong><br/><br/>' +
                  t("If you want to reset the language of the application, you can click on " )+ '<strong>' + t("'Change Language'")
        }
        facade.bus.emit('help:createView',homeConfigurationHelpviewOptions)

        filterHelpviewOptions = {
          $target:@$el.find('.filter-icon'),
          anchor:'left',
          position:'bottom-left',
          title:t('Filter') ,
          content:t('This icon activates/deactivates data filtering on Critical Violations. By default, the dashboard only shows information about Critical Violations, rather than showing data for ALL violations - this allows you to instantly see the most important flaws in the analyzed application.') +
            '<br/>' + t('All tiles and views in the dashboard are impacted by the data filter and will update their display accordingly.') + '<br/>' + t(" Only the following components are unaffected&#58; 'Action Plan view', 'Top Riskiest Components tile', 'Top Riskiest Transactions tile'")
        }
        facade.bus.emit('help:createView',filterHelpviewOptions)

        _.delay(()=>
          @resize()
         , 80)
        @$el
    })

    module = {
      initialize: (options) ->
        user = facade.context.get('user')
        @applications = new facade.models.applications.ApplicationsWithResults()
        @view = new HeaderView({el:options?.el, attributes:{userName:user.get('name'), applications:@applications}})
        @view.render()

        facade.bus.on('custom:add-menu-item', @updateMenuItems, @)

      updateMenuItems:(data)->
        @UserMenuItems.push(data)
        @view?.renderUserMenu()

      destroy: () ->
        @view.remove()
    }
    return module

  return HeaderModule
