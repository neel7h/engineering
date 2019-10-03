# specify the path to specific libraries and to typical path for packages declarations.

vendors = 'stem/base/3rdParties'
assets = 'stem/base/assets'
plugins = 'stem/plugins'

require.config
  waitSeconds: 60 # timeout for modules increased due to numerous web service queries blocking
  baseUrl: 'sources'
#urlArgs: "bust=" +  (new Date()).getTime()
  paths:
    'jquery': "#{vendors}/jquery/jquery.min"
    'jquery.noselect': "#{vendors}/jquery/plugins/noselect/1.0.3/jquery-noselect.min"
    'jquery.mousewheel': "#{vendors}/jquery/plugins/mousewheel/3.1.3/jquery-mousewheel.min"
    'jquery.ui': "#{vendors}/jquery/plugins/ui/1.10.3/jquery-ui-easing.min"
    'jquery.cookie': "#{vendors}/jquery/plugins/cookie/1.4.0/jquery-cookie.min"
    'jquery.splitter': "#{vendors}/jquery/plugins/splitter/0.14.0/jquery.splitter"
    'highcharts': "#{vendors}/highcharts/7.0.1/highcharts.src"
    'underscore': "#{vendors}/underscore/1.9.1/underscore.min"
    'backbone': "#{vendors}/backbone/1.1.2/backbone"
    'react': "#{vendors}/react/16.8.6/react.min"
    'propTypes': "#{vendors}/propTypes/15.6.2/propTypes.min"
    'reactDom': "#{vendors}/reactDOM/16.8.6/reactDOM.min"
    'materialUI': "#{vendors}/materialUI/4.2.1/materialUI.min"
    'jsonlint': "#{vendors}/jsonlint/jsonlint.min"
    'handlebars': "#{vendors}/handlebars/4.0.11/handlebars.min"
    'text': "#{vendors}/require/2.1.2/text.min"
    'eve': "#{vendors}/raphael/2.1.0/eve.min"
    'raphael': "#{vendors}/raphael/2.1.0/raphael.min"
    'spinner': "#{vendors}/spinner/1.0.0/spinner"
    'nibbler': "#{vendors}/nibbler/0.1.0/Nibbler.min"
    'i18next': "#{vendors}/i18n/2.0/i18next.min"
    'i18next-xhr': "#{vendors}/i18n/2.0/i18nextXHRBackend.min"
    'moment': "#{vendors}/i18n/moments/2.0.0/moment.min"
    'numberFormater': "#{vendors}/i18n/numeral/1.4.8/numeral.min"
    'numeralLocales': "#{vendors}/i18n/numeral/1.4.8/languages"

    'animo':'dashboard/plugins/animo/1.0.2/animo'
    'jQCloud':'dashboard/plugins/advancedUI/jQCloud/2.0.1/jqcloud'

    'simplePlaceholder':'dashboard/plugins/simplePlaceholder/master/jquery.simpleplaceholder'
    'highlight':'dashboard/plugins/codeHighlighter/highlight/8.4/highlight.min'
    'jquery.gridster': "dashboard/plugins/views/gridster/0.5.6/jquery.gridster.min"
    'modaldialog': 'dashboard/plugins/views/modaldialog/0.3.2/backbone-modaldialog.min'

    'cast.bootstrap': "#{assets}/bootstrap/0.3.2/bootstrap.min"
    'modules': 'dashboard/modules'
    'plugins': 'dashboard/plugins'
    'prototypes': 'dashboard/prototypes'
    'stem': 'stem'
    'stem.plugins': "#{plugins}"

  shim:

    'jsonlint':
      exports: 'jsonlint'
    'underscore':
      exports: '_'
    'jquery.noselect':
      deps: ['jquery']
      exports: 'jQuery.fn.noselect'
    'jQCloud':
      deps: ['jquery']
    'jquery.cookie':
      deps: ['jquery']
      exports: 'jQuery.fn.cookie'
    'jquery.mousewheel':
      deps: ['jquery']
    'jquery.ui':
      deps: ['jquery']
    'react':
      exports: 'React'
    'propTypes':
      deps: ['react']
      exports: 'PropTypes'
    'reactDom':
      deps: ['react']
      exports: 'ReactDOM'
    'materialUI':
      deps: ['reactDom']
      exports: 'MaterialUI'
    'animo':
      deps: ['jquery']
    'simplePlaceholder':
      deps: ['jquery']
    'jquery.splitter':
      deps: ['jquery']
      exports: 'jQuery.fn.split'
    'handlebars':
      exports: 'Handlebars'
    'highcharts':
      deps: ['jquery', 'highcharts']
      exports: 'Highcharts'
    'highcharts':
      deps: ['jquery']
    'backbone':
      deps: ['underscore', 'jquery']
      exports: 'Backbone'
    'modaldialog':
      deps : ['backbone']
    'moment':
      exports: 'moment'
    'nibbler':
      exports: 'Nibbler'
require ['stem/stem'
         'stem.plugins/logger'
         'stem.plugins/react'
         'stem.plugins/propTypes'
         'stem.plugins/reactDom'
         'stem.plugins/materialUI'
         'stem.plugins/bootstrap'
         'stem.plugins/utils'
         'plugins/i18n/i18n'
         'plugins/models/models'
         'plugins/views/views'
         'plugins/advancedUI/advancedUI'
         'plugins/utils/utils'
         'plugins/codeHighlighter/codeHighlighter'
         'plugins/simplePlaceholder/simplePlaceholder'
         'plugins/select/initializeSelect'
], (stem, loggerPlugin, reactPlugin, propTypesPlugin, reactDomPlugin, materialUIPlugin, bootstrapPlugin, utilsPlugin, i18nPlugin, modelsPlugin, viewPlugin, advancedUI, aedUtilsPlugin, codeHighlighter,simplePlaceholder) ->

  webApplication = new stem.WebApp()
  webApplication.usePlugins(stem.plugins.logger, reactPlugin, propTypesPlugin, reactDomPlugin, materialUIPlugin, bootstrapPlugin, i18nPlugin, utilsPlugin)
  webApplication.usePlugins(modelsPlugin, viewPlugin, advancedUI, aedUtilsPlugin, codeHighlighter, simplePlaceholder)

  require ['modules/login/Module'], (LoginModule) ->
    # FIXME should we not move those initialization modules somewhere else ?
    SessionModule = (facade) ->
      _ = facade._
      $ = facade.$
      t = facade.i18n.t

      # FIXME take from persitence plugin !! it is a duplicate !!
      LOCAL_STORAGE_WAR_IDENTIFIER = facade.base64.encode(window.location.pathname) + '_'
      window.LOCAL_STORAGE_KEY = LOCAL_STORAGE_WAR_IDENTIFIER + 'profiles'

      initialize: (options)->
        server = new facade.models.Server
        server.getData()

        $.ajaxSetup
          contentType: 'application/json'
          headers: { 'Accept-Language': localStorage.getItem("language").split('_')[0].toLocaleLowerCase() }
          timeout:60000

        $.ajaxPrefilter((settings, originalSettings, jqXHR)->
          dfd = $.Deferred();
          facade.bus.emit('setCurrentTime')

          # request success
          jqXHR.done((data, textStatus, jqXHR) ->
            dfd.resolve.apply this, Array.prototype.slice.call arguments
          )
          # request failure
          jqXHR.fail((jqXHR, statusText, errorText) ->
            if jqXHR.responseText.indexOf("/saml/") != -1
              return location.href = jqXHR.responseText;
            # Authentication required
            if ((jqXHR.status == 470 and @url.indexOf('login') == -1) or (jqXHR.status == 401 and @url.indexOf('logout') == -1) and not jqXHR.authRequest)
              options = {
                isHdOrSDEnabled: window.AAD_AVAILABLE or window.SD_AVAILABLE
              }
              facade.bus.emit('request:login', {options, dfd:dfd, statusText:statusText, errorText:errorText, ajaxParameters:@})
            else
              dfd.rejectWith jqXHR, Array.prototype.slice.call arguments
          )
          # Hijack the request promise into our own one
          jqXHRwrapper = dfd.promise(jqXHR)
          jqXHRwrapper.success = jqXHR.done;

          jqXHRwrapper.error = jqXHR.fail;
          return jqXHRwrapper
        )

        facade.bus.on('setCurrentTime', ()->
          localStorage.setItem('currentTime', new Date().getTime())
        )

        facade.bus.on('sessionAlert', (options)->
          timeoutDialog =  new facade.backbone.DialogView({
            samlSingleLogout: options.samlSingleLogout
            duration: options.sessionTimeLeft
            timeoutAlert: true
            title: 'Session Alert!'
            subTitle: ''
            samlConfig: true if options.serverData.get('securityMode') == 'saml' and AAD_AVAILABLE == true and (AED_AVAILABLE == true or  SD_AVAILABLE == true)
            message: facade.Handlebars.compile('<div><div class="dialogMessage">{{t "The Session is about to time out. Please click on Continue within the notified "}} </br>{{t "time in order to continue the current session."}}</div></div> ')
            login: 'Re-login'
            perform:'continue'
            action: 'continue'
            image: 'timeout-alert'
            button: true
            theme: 'background-orange'
            onPerform:()->
              facade.bus.emit('startSession',{that: options.that, serverData: options.serverData})
            onLogin:()->
              if options.serverData.get('securityMode') == 'saml'
                $.ajax('url': '../saml/login', 'type': 'GET', 'method': 'GET', 'headers': {}, 'async': false)
                  .success((result)=>
                    location.href = result
                )
              else
                facade.bus.emit('logout')
            })
          timeoutDialog.render()
        )

        facade.bus.on('startSession', (options)->
          $.ajax(url: REST_URL + 'ping', async: false)
          setTimeout(checkSessionTimeout.bind(options.that, facade, options.serverData),1000)
        )

        facade.bus.on('logout',()->
          if server.get('securityMode') == 'saml' 
            return location.href = '../saml/logout'
          logoutUrl = REST_URL + 'logout'
          type = 'GET'
          header = {}
          if server.get('securityMode') == 'integrated'
            logoutUrl = '../api/logout'
            type = "POST"
            token = document.cookie.match(new RegExp("(XSRF-TOKEN)=([^;]*)"))
            header = {'X-XSRF-TOKEN':token[2]}
          $.ajax('url': logoutUrl, 'type': type, 'method': type, 'headers': header, 'async': false)
            .always(()->
              location.replace(location.href.replace(location.hash, ''))
            )
        )

        couldProcessApplicationId = ()->
          if !SELECTED_APPLICATION_HREF? or '' == SELECTED_APPLICATION_HREF
            facade.bus.emit('require:application-selection')
            return false
          if SELECTED_APPLICATION_HREF.replace('/','') == CENTRAL_DOMAIN
            facade.bus.emit('require:application-selection', {domain:CENTRAL_DOMAIN})
            return false
          if /[\-\w\d]+\/applications\/(\d)+/.exec(SELECTED_APPLICATION_HREF)?.indexOf(SELECTED_APPLICATION_HREF) != 0
            facade.bus.emit('require:application-selection')
            return false
          return true
        return unless couldProcessApplicationId()

        portalConfiguration = new facade.models.configuration.Portal()
        portalConfiguration.on('user-filter:change', (options)->
          facade.bus.emit('global-filter-change', options);
          facade.bus.emit('global-filter-change:' + options.key, options);
        , this)
        violationIndex = new facade.models.ViolationsIndex({
          href: SELECTED_APPLICATION_HREF
        })
        violationIndex.getData({
          success:(data)=>
            localStorage.setItem('violationIndexStatus',data.get('status'))
          error:()=>
            localStorage.setItem('violationIndexStatus','')
        })
        portalConfiguration.getData({
          success:()=>
            webApplicationModules = portalConfiguration.get('configuration').webApplication.modules
            requireDependencies = []
            if portalConfiguration.get('configuration').alertTimeoutInterval then localStorage.setItem('alertTimeoutInterval', portalConfiguration.get('configuration').alertTimeoutInterval) else localStorage.setItem('alertTimeoutInterval', 10)
            for webApplicationModule in webApplicationModules
              requireDependencies.push('modules/' + webApplicationModule.key + '/Module')
              if webApplicationModule.includeCSS
                facade.css.includeCSSFile('sources/dashboard/modules/' + webApplicationModule.key + '/screen.css')

            require(requireDependencies,()->
              for i in [0..requireDependencies.length-1]
                key = requireDependencies[i]
                module = arguments[i]
                webApplication.register(key, module, webApplicationModules[i].parameters)

              UserContext = facade.backbone.Model.extend({
                url:REST_URL + 'user'
              })
              user = new UserContext()
              user.fetch().done(()->
                ApplicationContext = facade.backbone.Model.extend({
                  getData:(options)->
                    that = @
                    fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
                    application = new facade.models.applications.Application({href:@get('href')})
                    application.getData({
                      success:()->
                        snapshots = new facade.models.snapshots.Snapshots({href:application.getSnapshotsURL()})
                        snapshots.getData({
                          success:()->
                            that.set('application', application)
                            that.set('snapshots', snapshots)
                            that.set('scope', new facade.models.Scope({
                              businessCriterion:INIT_SELECTED_BUSINESS_HREF
                            }))

                            if INIT_SELECTED_SNAPSHOT_HREF?
                              snapshot = snapshots.findWhere({href:INIT_SELECTED_SNAPSHOT_HREF})
                            unless snapshot?
                              snapshot = snapshots.getLatest()
                            that.set('snapshot', snapshot)
                            window.INIT_SELECTED_SNAPSHOT_HREF = snapshot.get('href')
                            businessCriteria = new facade.models.ListOfBusinessCriteria({href: snapshot.get('configurationSnapshot').href})
                            businessCriteria.getData({
                              success:(results)->
                                if results.length == 1 and results[0].key == "60016"
                                  that.set('isSecurity',true)
                                else
                                  that.set('isSecurity',false)
                            })
                            that.set('theme','')
                            facade.bus.on('theme',(parameters)->
                              that.set('theme',parameters.theme)
                            )

                            technologies =  new facade.models.technologies.Technologies({
                              # technologies:application.listTechnologies()
                              technologies:snapshot.get('technologies')
                            })
                            technologies.pickTechnology(INIT_SELECTED_TECHNOLOGY)
                            that.set('technologies',technologies)

                            that.get('technologies').on('picked-technology:change',(data)->
                              facade.bus.emit('technologyFilter:change',data);
                            )

                            modules = new facade.models.applications.Modules({href:snapshot.get('href') + '/modules'})
                            server = new facade.models.Server()
                            modulesInPreviousSnapshot = new facade.models.snapshots.Snapshots({href: snapshot.get('previousSnapshotHref') + '/modules'})
                            $.when(server.fetch(),modules.fetch(),modulesInPreviousSnapshot.fetch()).then(()->
                              that.set('user', user)
                              that.set('modules', modules)
                              that.set('server', server)
                              localStorage.setItem('currentTime', new Date().getTime())
                              facade.bus.emit('startSession',{that: that, facade: facade, serverData: server })
                              that.set('modulesInPreviousSnapshot', modulesInPreviousSnapshot)
                              if INIT_SELECTED_MODULE_HREF?
                                module = modules.findWhere({href:INIT_SELECTED_MODULE_HREF})
                                if module?
                                  that.set('module', module)

                              fullOptions.success.apply(this, arguments)
                            ,()->
                              fullOptions.error.apply(this, arguments)
                            )
                          error:()->
                            fullOptions.error.apply(this, arguments)
                        })
                      error:(applicationModel, query)->
                        switch query.status
                          when 470 then console.info '' # Do nothing, ajax prefilter manages
                          when 403
                            facade.bus.emit('initialization:failure', {
                              errorType:t('Unauthorized access to application investigation')
                              errorMessage:t('You do not have the right to access to the selected application in Engineering Dashboard.')
                            })
                          else
                            facade.bus.emit('initialization:failure', {
                              errorType:t('Something got wrong')
                              errorMessage:t('You could not access the selected application in Engineering Dashboard.')
                            })
                    })
                })

                contextPlugin = {
                  id:'context'
                  Facade:
                    context:new ApplicationContext({href:SELECTED_APPLICATION_HREF})
                    portal:portalConfiguration
                }

                webApplication.use(contextPlugin)
                contextPlugin.Facade.context.getData({
                  success:()=>
                    webApplication.start(()->
                      console.info 'application started'
                      # snapshot = contextPlugin.Facade.context.get('snapshot')
                      # snapshots = contextPlugin.Facade.context.get('snapshots')

                      # if snapshot.get('href') != snapshots.getLatest().get('href')
                      #   appHref = contextPlugin.Facade.context.get('application').get('href')
                      #   window.reloadSnapshot = ()->
                      #     window.location = '#' + appHref;
                      #     window.location.reload(true);
                      #   facade.bus.emit('notification:persistent-message',{
                      #     title:t('Data out of date')
                      #     message:t('You are not investigating the latest analysis results available. Please follow this <a onclick=\"reloadSnapshot()\">link</a> to get access to latest data available')
                      #     })
                    )
                  error:()->
                    facade.bus.emit('initialization:failure', arguments)
                })
              )
            )
          error:()->
            facade.bus.emit('initialization:failure', {
              errorType:'ced.json file contains errors.'
            })
        })

    checkSessionTimeout = (facade, serverData)->
      alertTimeoutInterval = localStorage.getItem('alertTimeoutInterval')
      sessionTimeLeft = serverData.get('sessionTimeout') - parseInt(Math.abs(new Date().getTime() - Number(localStorage.getItem('currentTime')))/1000)
      if sessionTimeLeft > alertTimeoutInterval
        setTimeout(checkSessionTimeout.bind(@, facade, serverData), 1000)
      else
        facade.bus.emit('sessionAlert',{that: @, serverData: serverData, sessionTimeLeft: sessionTimeLeft})

    webApplication.bus.on('initialization:failure', (options)->
      require ['modules/errorPage/Module'], (errorPageModule) ->
        webApplication.register('errorPage', errorPageModule, {
          el:'#error-page-display'
          errorType:options?.errorType
          errorMessage:options?.errorMessage
        })
        webApplication.start('errorPage')
    )

    webApplication.bus.on('require:application-selection', (options)->
        console.info 'require application selection'
        require ['modules/applicationSelection/Module'], (applicationSelection) ->
          webApplication.register('applicationSelection', applicationSelection, {domain:options?.domain, el:'#application-selection-container'})
          webApplication.start('applicationSelection')
    )

    webApplication.bus.on('require:adminPage', (options)->
      require ['dashboard/reactModules/adminPage/Module'], (app) ->
        webApplication.register('app', app)
        webApplication.start('app')
    )

    webApplication.register('localizationInit', (facade)->
      return {
        initialize:(options)->
          portalConfiguration = new facade.models.configuration.Portal()
          portalConfiguration.getData({
            success:()=>
              languageList = [{label: "English", value: "en_US"},
                              {label: "Chinese", value: "zh_CN"},
                              {label: "French", value: "fr_FR"},
                              {label: "Spanish", value: "es_ES"},
                              {label: "German", value: "de_DE"},
                              {label: "Japanese", value: "ja_JP"},
                              {label: "Portuguese", value: "pt_PT"},
                              {label: "Turkish", value: "tr_TR"},
                              {label: "Korean", value: "ko_KR"}]
              addedLanguages = _.uniq(portalConfiguration.get('configuration').customLanguages, _.property('value'))
              _.each(addedLanguages, (language) =>
                languageList.push(language)
              )
              availableLanguages = []
              deferredArr = _.map(languageList, (language) ->
                return $.ajax(url: 'locales/' + language.value + '/translation.json', async: false)
                  .done(()->
                    localStorage.setItem("language", language.value) if language.label.toLowerCase() == (portalConfiguration.get('configuration').defaultLanguage?.toLowerCase() || "english") if !localStorage.getItem("language")
                    availableLanguages.push(language)
                )
              )
              $.when.apply(deferredArr).then(()->
                localStorage.setItem("availableLanguages", JSON.stringify(_.sortBy(availableLanguages, "label")))
                localStorage.setItem("language", "en_US") if !localStorage.getItem("language")
                language = localStorage.getItem("language")
                document.body.className = document.body.className + ' ' + language.toLocaleLowerCase()
                console.info('Initializing application localization using language:', language)
                facade.i18n.init({lng: language, returnEmptyString: false, debug: false}, ()->
                  webApplication.register('login', LoginModule, {el: '#message'})
                  webApplication.start('login')
                  webApplication.register('session', SessionModule)
                  webApplication.start('session')
                );
              )
              $('html').attr('lang','en') if localStorage.language == 'en_US'
            error:()->
              facade.bus.emit('initialization:failure', {
                errorType:'ced.json file contains errors.'
              })
          });
      }
    ,{})

    webApplication.start('localizationInit')
