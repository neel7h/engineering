###
  applications provides the models to access general information regarding applications.

  REST-API documentation : http://confluence/display/PdtInt/Portfolio+API
###
snapshots = (_, BackboneWrapper) ->
  # FIXME expose global variables such as health-factors to improve reusability
  HEALTH_FACTORS = ["60011", "60012", "60013", "60014", "60016","60017"]

  Snapshot = BackboneWrapper.BaseModel.extend({

    getId: ()->
      items = @get('href').split('/')
      items[items.length - 1]

    createBusinessCriteriaConfiguration:(options)->
      options = _.extend({},options,{href:@get('configurationSnapshot').href + '/business-criteria'})
      return new BusinessCriteriaConfiguration(options)

    getPreviousSnapshot:()->
      return @collection.findWhere({href: @get('previousSnapshotHref')})

    getFirstSnapshot:()->
      return @collection.findWhere({href: @get('firstSnapshotHref')})

    getLastTwoSnapshotIds:()->
      snapshotIds = []
      if @get('href') == @get('firstSnapshotHref')
        snapshotIds.push(@getId())
        return snapshotIds
      else if @get('href') != @get('previousSnapshotHref')
        previousSnapshot = @get('previousSnapshotHref').split('/')
        snapshotIds.push(previousSnapshot[previousSnapshot.length-1])
      snapshotIds.push(@getId())
      return snapshotIds

    isLatest:()->
      return @get('href') == @get('latestSnapshotHref')
  })

  Snapshots = BackboneWrapper.BaseCollection.extend({
    model: Snapshot
    url: ()->
      REST_URL + this.href

    initialize:(options)->
      this.href = options.href

    parse:(data)->
      return if data.length == 0
      data.sort((a,b)->
        return a.annotation.date.time - b.annotation.date.time
      )
      firstSnapshotHref = data[0].href
      if data.length >1
        previousSnapshotHref = data[data.length-2].href
      else
        previousSnapshotHref = data[0].href
      latestSnapshotHref = data[data.length-1].href

      for snapshot in data
        snapshot.previousSnapshotHref = previousSnapshotHref
        snapshot.firstSnapshotHref = firstSnapshotHref
        previousSnapshotHref = snapshot.href
        snapshot.latestSnapshotHref = latestSnapshotHref
      return data

    getLatest: ()->
      max = 0
      latest = null
      for model in @models
        time = model.get('annotation').date.time
        if time > max
          latest = model
          max = time
      latest
  })

  BusinessCriteriaConfiguration = BackboneWrapper.BaseCollection.extend({
    url: ()->
      REST_URL + this.href

    initialize:(options)->
      @href = options.href
      @filterHealthFactor = options.filterHealthFactor

    parse:(data)->
      return data unless @filterHealthFactor
      result = []
      for sample in data
        result.push(sample) if HEALTH_FACTORS.indexOf(sample.key) >=0
      return result


  })

  return {
  Snapshot
  Snapshots
  }
