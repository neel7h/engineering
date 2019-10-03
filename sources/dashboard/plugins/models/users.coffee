###
  users provides the models for basic user information
###
users = (_, BackboneWrapper) ->
  ###
  CurrentUser provides basic information for the logged in user.
  * isAdmin method tells whether the user is an administrator or not.
  * getName returns the user name
  ###
  CurrentUser : BackboneWrapper.BaseModel.extend({
    url:REST_URL + 'user'
    isAdmin:()->
      @get('administrator')
    getName:()->
      @get('name')
  })
