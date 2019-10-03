NoSourceCodeViewer = (facade, models)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t


  return backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'
    template:Handlebars.compile('<h2>{{t "Source code"}}</h2>
      <p>{{t "Source code is not available for selected object. Multiple reasons could explain source code not to be available, including but not limited to:"}}</p>
      <ul>
        <li>{{t "Source code was not integrated for security reasons"}}</li>
        <li>{{t "you are not accessing the latest analysis (source code is only available to last analysis)"}}</li>
        <li>{{t "you could be facing platform issue"}}</li>
      </ul>
      <p>{{t "Please contact your administrator if you think you should have seen source code."}}</p>')

    render:()->
      @$el.html(@template)
      return @$el
  })
