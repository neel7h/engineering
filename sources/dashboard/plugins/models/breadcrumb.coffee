breadcrumb = (_, BackboneWrapper) ->

  # quality model for breadcrumb path + context data (e.g. module/technology filter)
  QualityModelInformation = BackboneWrapper.BaseModel.extend({
    url:()->
      criteria = @get('criteria').join(',').replace(',all','')
      REST_URL + SELECTED_APPLICATION_HREF + '/results?quality-indicators=(' + criteria + ')&modules=$all&technologies=$all'

    hasModule:()->
      return @get('module')?

    hasTechnology:()->
      return @get('technology')?

    sameModule:(moduleSnapshotHref, moduleHref)->
      href = moduleSnapshotHref.split('/').slice(0,3).join('/')
      href == moduleHref

    getContextCriterion:()->
      criteria = @get('criteria')
      return null unless criteria?
      criterion = criteria[criteria.length-1]
      criterion = criteria[criteria.length-2] if 'all' == criterion
      return null unless criterion?
      return criterion

    getTechnologiesInResult:(results)->
      values = []
      results = results.technologyResults if results.technologyResults?
      for result in results
        values.push(result.technology)
      return values

    availableTechnologies:()->
      criterion = @getContextCriterion()
      availableTechnologies = ['-1']
      applicationResults = @get('0')?.applicationResults
      return availableTechnologies unless applicationResults?
      for result in applicationResults
        if criterion == result.reference.key
          selectedResult = result
          break
      return availableTechnologies unless selectedResult?
      if (@hasModule())
        module = @get('module')
        for moduleResult in selectedResult.moduleResults
          if module == moduleResult.moduleSnapshot.href.split('/').slice(0,3).join('/')
              return availableTechnologies.concat(@getTechnologiesInResult(moduleResult))
      else
        return availableTechnologies.concat(@getTechnologiesInResult(selectedResult))
      return availableTechnologies

    availableModules:()->
      criterion = @getContextCriterion()
      availableModules = ['-1'] # -1 means all modules
      applicationResults = @get('0')?.applicationResults
      return availableModules unless applicationResults?
      for result in applicationResults
        if criterion == result.reference.key
          selectedResult = result
          break
      return availableModules unless selectedResult?
      if (@hasTechnology())
        technology = @get('technology')
        for moduleResult in selectedResult.moduleResults
          technologiesInResult = @getTechnologiesInResult(moduleResult)
          if technologiesInResult.indexOf(technology) > -1
            href = moduleResult.moduleSnapshot.href.split('/').slice(0,3).join('/')
            availableModules.push(href)
      else
        for moduleResult in selectedResult.moduleResults
          href = moduleResult.moduleSnapshot.href.split('/').slice(0,3).join('/')
          availableModules.push(href)

      return availableModules

    listResults:()->
      results = []
      applicationResults = @get('0')?.applicationResults
      return results unless applicationResults?
      module = @get('module')

      for result in applicationResults
        processedResult = {
          key:result.reference.key
          name:result.reference.name
          shortName:result.reference.shortName
          type:result.type
        }
        results.push(processedResult)
      allTechnicalCriteriaIndex = @get('criteria').indexOf('all')
      if  allTechnicalCriteriaIndex > -1
        processedResult = {
          key:'all'
          name:'All Rules...'
          shortName:null
          type:'technical-criteria'
        }
        results.splice(allTechnicalCriteriaIndex,0,processedResult)
      results
  })



  return {
    QualityModelInformation
  }
