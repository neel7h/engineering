###
  Defines the license component.
###
define [],->
  LicenseModule = (facade) ->
    _ = facade._

    LicenseView = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<div class="license-state hide">
        <div class="message">
          <h2>{{t "this software is subject to a limited access."}}</h2>

          {{#if restricted}}
          <p>{{t "There are too many authorized users to connect to your Engineering Dashboard."}}</p>
          <p>{{{t "To avoid this limitation, you can contact your <a>CAST Administrator</a> to update your licensing terms & conditions."}}}</p>
          {{else}}
              {{#if isAdmin}}
              <p>{{t "You are connected as Administrator. This role is only for inspecting results on analysis machine. Action planning is not available."}}</p>
              {{else}}
              <p>{{t "We were not able to get proper license information; either your licence is missing or it is not valid."}}</p>
              {{/if}}
          {{/if}}
        </div>
      </div>')

      events:
        'click a':'contactCASTManager'

      initialize:(options)->
        @restricted = options.statusType == 'exceeded'

      contactCASTManager:()->
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
        urlsStore.fetch().done(()->
          tags = {}
          window.location.href = urlsStore.makeUrl "license-key-request", tags
        )


      render:()->
        isAdmin = facade.context.get('user')?.get('administrator')
        @$el.html(@template({
          restricted:@restricted
          isAdmin:isAdmin
        }))
        @$el
    })

    module = {
      initialize:(options) ->
        @options = facade._.extend({},options)
        licenseState = facade.context.get('server')?.licenseStatus()
        incorrectLicences = ['NO_LICENSE_KEY','INVALID_LICENSE_KEY','CANNOT_ACCESS_LICENSE_KEY','INVALID_LICENSE_FILE']
        exceededLicences = ['GLOBAL_ACCESS_TOKENS_EXCEEDED','UNIT_ACCESS_TOKENS_EXCEEDED']

        if incorrectLicences.indexOf(licenseState) >= 0
          @processInvalidLicence(licenseState, 'invalid')
        if exceededLicences.indexOf(licenseState, 'exceeded') >= 0
          @processInvalidLicence(licenseState, 'exceeded')
        # @processInvalidLicence(licenseState, 'exceeded')

      processInvalidLicence:(status, statusType)->
        @view = new LicenseView({
          el: @options.el
          statusType:statusType
        })
        @view.$el.parents().addClass('aed-lqm')
        @view.render()

      destroy:()->
        @view.remove()
    }
    return module

  return LicenseModule
