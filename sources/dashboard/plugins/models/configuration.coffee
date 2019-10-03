configuration = (_, BackboneWrapper) ->

  hash = (string) ->
    result = 0;
    return result unless string?
    return result  if string.length == 0
    for i in [0..string.length-1]
      char = string.charCodeAt(i)
      result = (result << 5) - result + char
      result |= 0
    return result.toString(16)

  HEALTH_FACTORS = ['60011', '60012', '60013', '60014', '60016','60017']


  Portal = BackboneWrapper.BaseModel.extend({
    userSettingsStorageKey:hash(window.location.pathname) + '_userSettings'
    defaultSettings:{
      criticalsOnly:true #default values
    }
    url : CED_JSON

    getTQIifBCisFiltered:(business)->
      return business unless business?
   	  return business unless @filterHealthFactors()
      return '60017' if (HEALTH_FACTORS.indexOf(business) == -1)
      return business


    filterHealthFactors:()->
      configuration = @get('configuration')?.filterHealthFactor
      return configuration if configuration?
      return true

    getDefaultPanels:()->
      localProfiles = localStorage.getItem(LOCAL_STORAGE_KEY)
      if localProfiles?
        profiles = JSON.parse(localProfiles)
        return profiles[0]?.areas[0]?.panels

      profiles = @get('configuration')?.profiles.slice(0)
      return profiles[0]?.areas[0]?.panels

    getDefaultProfiles:()->
      localProfiles = localStorage.getItem(LOCAL_STORAGE_KEY)
      if localProfiles?
        profiles = JSON.parse(localProfiles)
        return profiles
      profiles = @get('configuration')?.profiles.slice(0)
      return profiles

    setFilterSetting:(key, value)->
      this.get('configuration').parameters.filters[key] = value;
      this.trigger('user-filter:change', {key:key, value:value})
      this.saveUserSettings()

    getFilterSetting:(key)->
      return  this.get('configuration').parameters.filters[key];

    saveUserSettings:()->
      localStorage.setItem(this.userSettingsStorageKey, JSON.stringify(this.get('configuration').parameters))

    userIsFiltering:()->
      filters = this.get('configuration').parameters.filters
      for key, value of filters
        return true if value
      return false

    resetFilters:()->
      filters = @get('configuration').parameters.filters
      for key, value of this.defaultSettings
        continue if (this.defaultSettings[key] == filters[key])
        this.setFilterSetting(key, value)
      @saveUserSettings()

    parse:(data)->
      parameters = localStorage.getItem(this.userSettingsStorageKey)
      parameters = if parameters? then JSON.parse(parameters) else {}
      parameters.filters = _.extend({},  this.defaultSettings, parameters.filters)
      _.extend(data.configuration.parameters, parameters)
      return data
  })

  return {
    Portal
  }
