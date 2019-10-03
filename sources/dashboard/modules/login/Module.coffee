###
  Defines the application help and possible interactions.
###
define ['text!./login.hbs'], (loginTemplate)->

  LoginModule = (facade) ->
    Backbone = facade.backbone
    Handlebars = facade.Handlebars
    _ = facade._
    $ = facade.$
    t = facade.i18n.t

    # inline url stores for lost password/request access and so issues
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
    urlsStore.fetch() # TODO possible source of bugs, we should find other ways to use it

    UserContext = facade.backbone.Model.extend({
      url:REST_URL + 'user'
    })

    user = null

    LoginPageView = Backbone.View.extend({
      tagName: 'div'
      id: 'login-page'

      template: Handlebars.compile(loginTemplate)
      events:
        'submit form': 'submit'
        # "keyup div.login-authentication.login-text > input" : "logOnEnter"
        # "click div.login-authentication > a.login-action": "login"
        "click div#login-request-choice   input": "refreshChoices"
        "click div.login-request-access > a.login-action": "requestAccess"
        "click a#login-request-access-action": "showAccess"
        "click a#login-request-access-back": "hideAccess"
        'click input[type=checkbox]': 'aedVsAad'
        'focus input': 'resetErrorArea'
        'click a': 'resetErrorArea'

      templateHelpers: ()->
        return {
          castVersion: VERSION
        }

      submit: (event)->
        event.preventDefault()
        event.stopPropagation()
        window.external?.AutoCompleteSaveForm?(document.getElementById('credentials'));
        @login(event)
        return false

      resetErrorArea: ()->
        @$err = @$err or @$el.find('.login-error p')
        if 'block' == @$err.css('display')
          @$err.css('display', 'none')
          @$el.find('#login-button').show()

      aedVsAad: (event)->
        $loginTitle = @$el.find('#login-title')
        if $(event.target).prop('checked')
          $loginTitle.addClass('aed')
        else
          $loginTitle.removeClass('aed')

      showAccess: ()->
        @$el.find('.actions .login').css('display': 'none')
        @$el.find('.actions .cannot-access').css('display', 'table')
        @$('#login-username input').val('')
        @$('#login-password input').val('')

      hideAccess: ()->
        @$el.find('.actions .login').css('display': 'table')
        @$el.find('.actions .cannot-access').css('display', 'none')
        @$('#login-userlost input').val('')

      initialize: () ->
        @isHdOrSDEnabled = options?.isHdOrSDEnabled
        $(window).on('resizeEnd', @onRender)

      render: () ->
        this.$el.html(@template({isHdOrSDEnabled:@isHdOrSDEnabled, castVersion: VERSION, configureRequestAccess: @configureRequestAccess}));
        @onRender()
        if(navigator.appVersion.match(/MSIE [\d.]+/))
          facade.polyfill.placeholder(@$el.find('.actions input'))
        return this;

      onShow:() ->
        require ['utils/styles','raphael','gauge', 'utils/treemapChart','spinner'],()->
          # just load libraries on downtimes

      onClose: () ->
        $(window).off('resizeEnd', @onRender)
        @$('#login-request-access-back').off('click')

      onRender: () ->
        if navigator.userAgent.match(/iPhone/i) or navigator.userAgent.match(/iPod/i) or navigator.userAgent.match(/iPad/i) or navigator.userAgent.match(/android/i)
          @$('.login-text>input').width('325')
          @$('a#login-guidelines').css('font-size','0.73em');
          @$('a#login-guidelines').css('letter-spacing', '0.2em');

      showLogin: (options) ->
        LoginPageView.currentDialog.isHdOrSDEnabled = options.isHdOrSDEnabled
        unless LoginPageView.currentDialog.loginDeferred?
          LoginPageView.currentDialog.loginDeferred = $.Deferred()
          portalConfiguration = new facade.models.configuration.Portal()
          portalConfiguration.getData({
            success: ()=>
              @configureRequestAccess = portalConfiguration.get('configuration').requestAccess or false
              $(options.el).html(LoginPageView.currentDialog.render().$el)
            error: ()->
              @configureRequestAccess = false
              $(options.el).html(LoginPageView.currentDialog.render().$el)
              facade.bus.emit('initialization:failure', {
                errorType: 'ced.json file contains errors.'
              })
          })
        return LoginPageView.currentDialog.loginDeferred

      logoutData: (message, logoutURL, type, header, server) ->
        @$el.find('.login-error p').html(message?.get('message')).css('display','block')
        @$el.find('#login-button').hide()
        if server.get('securityMode') == 'saml'
          return location.href = '../saml/logout'
        $.ajax('url': logoutURL, 'type': type, 'method': type, 'headers': header, 'async': false)

      login: (event) ->
        loginUrl = REST_URL + 'login'
        $.ajax('url': '../rest/server', 'type': 'GET', 'method': 'GET', 'headers': {}, 'async': false)
          .always((result)=>
            loginUrl = '../api/user' if result.securityMode == 'integrated'
        )
        event.preventDefault() ## useful ?
        @$el.find('input').blur()
        $('.login-action').addClass('login-action-submit')
        that = @
        jqXHR = $.ajax
          'url': loginUrl
          'headers':
            "Authorization": "Basic "+facade.base64.encode("#{@$('#login-username>input').val()}:#{@$('#login-password>input').val()}")
          'success': (data, textStatus, jqXHR)=>
            applications = new facade.models.applications.Applications()
            applications.getData({
                success:()=>
                  #TODO : Cleanup this code
                  # unsuccessful cases
                  if applications.length == 0
                    server = new facade.models.Server()
                    server.getData({
                      success:()=>
                        facade.bus.emit('setCurrentTime')
                        type = 'GET'
                        logoutURL = REST_URL + 'logout'
                        header = {}
                        if server.get('securityMode') == 'integrated'
                          logoutURL = '../api/logout'
                          type = "POST"
                          token = document.cookie.match(new RegExp("(XSRF-TOKEN)=([^;]*)"))
                          header = {'X-XSRF-TOKEN':token[2]}
                        if applications.domainsCount() == 0 # no domains available
                          message = urlsStore.findWhere({id:'login-invalid-db-setup'}) or 'Database connection issue'
                          @logoutData(message, logoutURL, type, header, server)
                          return
                        if applications.domainsAdgCount() == 0 # no ADG domains available
                          message = urlsStore.findWhere({id:'login-invalid-adg-db-setup'}) or 'Database connection issue'
                          @logoutData(message, logoutURL, type, header, server)
                          return

                        if server.get('license')?.status == 'NO_LICENSE_KEY'
                          message = urlsStore.findWhere({id:'no-license-key'}) or 'Forbiden access'
                          @logoutData(message, logoutURL, type, header, server)
                        else
                          message = urlsStore.findWhere({id:'login-invalid-user'}) or 'Forbiden access'
                          @logoutData(message, logoutURL, type, header, server)
                      error:(e)->
                        console.error 'cannot get server information'
                    })
                    return

                  facade.bus.emit('login:successful') # to perform some actions between login view disappearing and query resolution

                  name = user?.get('name')
                  user = new UserContext()
                  user.fetch().done(()->
                    newName = user.get('name')
                    if name? and name != newName
                      window.location = './index.html#' + SELECTED_APPLICATION_HREF

                    LoginPageView.currentDialog.$el.hide()
                    LoginPageView.currentDialog.loginDeferred.resolve {}, {}
                    LoginPageView.currentDialog = null # The ajax events are removed when the dialog box closes

                  )
                error:()->
                  message = t('An unknown error occurred while trying to fetch application list')
                  that.$el.find('.login-error p').html(message?.get('message')).css('display','block')
                  @logoutData(message, logoutURL, type, header, server)
              })

        # ERROR HANDLER : SHOW MESSAGE
          'error': (jqXHR, textStatus, errorThrown)=>
            message = urlsStore.findWhere({id:'login-invalid-data'})?.get('message')
            if jqXHR.status == 503
              message = jqXHR.responseJSON?.message if jqXHR.responseJSON?.message?
            @$el.find('.login-error p').html(message).css('display','block')
            @$el.find('#login-button').hide()

          'complete': (jqXHR, textStatus)=>
            @$('.login-action').removeClass('login-action-submit')
        jqXHR.authRequest = true;

      refreshChoices: (event) ->
        disabled = @$("input#login-request-access").is(':checked')
        @$('#login-userlost input').prop('disabled', disabled).val('')

      requestAccess: (event) ->
        tags = {}
        @$('div.login-text.login-request-access>input').each (index,element)-> tags[element.parentElement.id] = if element.value then element.value else 'unknown'
        for requestChoice in ['login-reset-password', 'login-request-access']
          if @$("input##{requestChoice}").is(':checked')
            if 'login-reset-password' == requestChoice
              return this if @$('#login-userlost input').val() == ''
            window.location.href = urlsStore.makeUrl requestChoice, tags
        return this;


    } , {

      currentDialog: null

    # nextReqDeferred is resolved as soon as the replayed AJAX request (with authentication headers) succeed
      authenticate: (options, nextReqDeferred, textStatus, textError)->
        if not LoginPageView.currentDialog?
          LoginPageView.currentDialog=new LoginPageView()
        LoginPageView.prototype.showLogin(options)

    })

    module = {
      initialize: (options) ->
        @el = options.el
        localStorage.removeItem('reportType')
        localStorage.removeItem('reportGenerating')
        # user = new UserContext()
        # user.fetch()
        facade.bus.on('request:login', @requestLogin, @)

      requestLogin:(parameters)->
        options = parameters.options
        isHdOrSDEnabled = options.isHdOrSDEnabled
        dfd = parameters.dfd
        statusText= parameters.statusText
        errorText = parameters.errorText
        LoginPageView.authenticate({el:@el, isHdOrSDEnabled:isHdOrSDEnabled}, dfd, statusText, errorText).done((headers, data)=>
          @headers = _.extend (@headers ? {}), headers
          @data    = _.extend (@data ? {}), data
          $.ajax(parameters.ajaxParameters).then(dfd.resolve, dfd.reject)
        )
    }
    return module

  return LoginModule
