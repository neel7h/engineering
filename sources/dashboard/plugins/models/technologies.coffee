technologies = (_, BackboneWrapper) ->

  Technologies = BackboneWrapper.BaseModel.extend({
    _selectedTechnology:null
    # initialize:(data, options)->
    pickTechnology:(technology, options)->
      silent = options?.silent
      if technology? and !isNaN(technology)
        technology = technology.toString()
      technologies = @get('technologies') or []
      index = technologies.indexOf(technology)
      if technology? and technology != "-1" and index == -1
        return
      newselectedTechnology = technologies[index] or null
      if newselectedTechnology != @_selectedTechnology
        @_selectedTechnology = newselectedTechnology
        @trigger('picked-technology:change', {selectedTechnology:@_selectedTechnology}) unless silent

    getSelected:()->
      return @_selectedTechnology

    getSelectedEncoded:()->
      if @_selectedTechnology
        return encodeURIComponent(@_selectedTechnology)
      return @_selectedTechnology

    asSelector:(options={})->
      selectedTechnology = @getSelected()
      data = [{
        label:if options.translate? then options.translate('All Technologies') else 'All Technologies'
        value:-1
        selected:selectedTechnology == null
      }]
      for technology in @get('technologies')
        data.push({
          label:technology
          value:technology
          selected:selectedTechnology == technology
        })
      return data
  })

  return {
    Technologies
  }
