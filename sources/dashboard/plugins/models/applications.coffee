###
  applications provides the models to access general information regarding applications.

  REST-API documentation : http://confluence/display/PdtInt/Portfolio+API
###
applications = (_, BackboneWrapper) ->

  Snapshot =  BackboneWrapper.BaseModel.extend({

    getId:()->
      items  =@get('href').split('/')
      items[items.length-1]

  })

  Snapshots = BackboneWrapper.BaseCollection.extend({
    model:Snapshot
    url:()->
      REST_URL + this.href

    initialize:(options)->
      this.href = options.href

    getLatest:()->
      max = 0
      latest = null
      for model in @models
        time = model.get('annotation').date.time
        if time > max
          latest = model
          max = time
      latest
  })

  _DatabaseDomains = BackboneWrapper.BaseCollection.extend({
    url: REST_URL.replace(/\/$/, "") # Remove the trailing slash for REST API on WebSphere
  })

  ###
    Application provide basic information relative to a given analysed application.
    * getModulesURL provides the url to get the application modules
    * getSnapshotsURL provides the url to get the listing of the application snapshots
    * getResultsURL provides the url to get the application results
    * getId provides the application id (:domain/application/:centralId)
    * getName provides the application name
    * listTechnologies provides the list of technologies for the application
  ###
  Application = BackboneWrapper.BaseModel.extend({
    url: ->
      REST_URL + @get('href')

    getModulesURL:()->
      @get('modules')?.href or ''
    getSnapshotsURL:()->
      @get('snapshots')?.href or ''
    getResultsURL:()->
      @get('results')?.href or ''
    # TODO this method (getId) has no value when asking a central database : it will always be null. I suggest to delete this method
    getId:()->
      @get('origin')?.href or @get('href') or ''
    getName:()->
      @get('name') or ''
    listTechnologies:()->
      @get('technologies')?.slice(0) or []
  })


  Applications = BackboneWrapper.BaseCollection.extend({
    model:Application

    comparator:(model)->
      model.get('name').toLocaleLowerCase()

    getData:(options)->
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      @domains = new _DatabaseDomains()
      @domains.fetch().done(()=>
        ADGDomains = @domains.where({dbType:'ADG'})
        deferred = []
        for domainModel in ADGDomains
          appList = new _Applications({href:domainModel.get('applications').href})
          ((appList)->
            promise = appList.fetch()
            promise.done(()=>
              for app in appList.models
                that.add(app);
            )
            deferred.push(promise)
          )(appList)

        $.when.apply($, deferred).done(()->
          fullOptions.success.apply(this, arguments)
        ).fail(()->
          fullOptions.error.apply(this, arguments)
        )
      )

    domainsCount:()->
      @domains.length

    domainsAdgCount:()->
      @domains.where({dbType:'ADG'}).length

    list:()->
      return @adgValidModels.slice(0) if @adgValidModels
      @adgValidModels = []
      for application in @models
        @adgValidModels.push(application) if application.getId()?
      return @adgValidModels.slice(0)

  })

  ###
    Applications collection provides the listing of available applications
  ###
  _Applications = BackboneWrapper.BaseCollection.extend({
    model: Application

    url:()->
      REST_URL + @domainUrl

    initialize:(options)->
      @domainUrl = options.href

    parse:(data)->
      validApplications = []
      for application in data
        validApplications.push(application)
        application.origin = {href:application.href} # for backward compatibility
      validApplications
  })


  _ApplicationWithResult = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href

    initialize:(options)->
      @href = options.href

    parse:(data)->
      results = []
      for sample in data
        result = {
          name: sample.name
          href: sample.href
        }
        results.push(result)
      results
  })

  ApplicationsWithResults = BackboneWrapper.BaseCollection.extend({

    initialize:(data, options)->
      @options = _.extend({},options)

    comparator:(model)->
      model.get('name').toLocaleLowerCase()

    getData:(options)->
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      domains = new _DatabaseDomains()
      domains.fetch().done(()=>
        ADGDomains = domains.where({dbType:'ADG'})
        deferred = []
        filteredDomain = _.findWhere(ADGDomains, {href:@options.domain})
        if @options.domain?
          for domainModel in ADGDomains
            continue if @options.domain != domainModel.get('href')
            model = domainModel
            break
          filterDomain = model?
        for domainModel in ADGDomains
          continue if filterDomain and @options.domain != domainModel.get('href')
          appList = new _ApplicationWithResult({href:domainModel.get('applications').href})
          ((appList)->
            promise = appList.fetch()
            promise.done(()=>
              for app in appList.models
                that.add(app);
            )
            deferred.push(promise)
          )(appList)

        $.when.apply($, deferred).done(()->
          fullOptions.success.apply(this, arguments)
        ).fail(()->
          fullOptions.error.apply(this, arguments)
        )
      )
  })


  Module = BackboneWrapper.BaseModel.extend({
    url: ->
      REST_URL + @get('href')
    parse:(data)->
      data.href = data.href.split('/snapshots/')[0]
      data

    getName:()->
      @get('name')
    getId:()->
      items  = @get('href').split('/')
      items[items.length-1]
    getHREF:()->
      @get('href')
    getSnapshotsHREF:()->
      @get('href') + '/snapshots'
  })

  Modules = BackboneWrapper.BaseCollection.extend({
    model:Module
    url: ()->
      REST_URL + @href

    initialize:(options)->
      @href =  options?.href or SELECTED_APPLICATION_HREF + '/modules'



    list:()->
      return @models.slice(0)

  })

  return {
    Application
    Applications
    ApplicationsWithResults
    Module
    Modules
  }
