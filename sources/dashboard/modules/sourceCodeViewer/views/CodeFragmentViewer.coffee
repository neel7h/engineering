CodeFragmentViewer = (facade, models)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  # TODO move to plugins
  escape = (()->
    tagsToReplace = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;'
    }
    return (string) ->
      string.replace(/[&<>]/g, (tag) ->
        tagsToReplace[tag] || tag;
      )
    )()

  Viewer = backbone.View.extend({
    template:Handlebars.compile('
<p class="additional-info">Additional information bookmark</p>

{{#if name}}<a href="source.html{{viewFile}}?startline={{objectStartLine}}&endline={{objectEndLine}}&issueType={{issueType this}}&highlightBookmark={{highlightBookmark}}&secondary={{secondary}}" target="_blank" title="{{t "View the whole file content in a separate window."}}" class="view-file">{{t "View File"}}</a><h3>{{name}}</h3><hr>{{/if}}
<div class="table-container"><table><tbody></tbody></table></div>
          <div class="show-more">{{t "Show more"}}</div>')
    noCodeTemplate:Handlebars.compile('<tr><td title="{{t "source code is not available for viewing"}}">({{t "not available"}})</td></tr>')
    codeTemplate:Handlebars.compile('{{#each linesOfCode}}
          <tr><td class="line-number {{highlightLineNumber @index ../this}}" data-line-number="{{lineNumber @index ../this}}"></td><td class="{{highlight @index ../this}}"><pre><code class="">{{{this}}}</code></pre></td></tr>
        {{/each}}')

    events:
      'click .show-more':'showMore'

    showMore:()->
      @model.fetchMore().done(()=>
        @_renderFragment()
      )

    initialize:(options)->
      @model = new models.SourceCode(options)
      @model.set({secondary:options.secondary})

    _prepareLinesOfCode:(data)->
      bookmarkStart = data.objectStartLine - data.startLine
      bookmarkEnd = data.objectEndLine - data.startLine
      if data.highlightBookmark
        for index in [0..data.linesOfCode.length-1]
          lineOfCode = data.linesOfCode[index]
          if index < bookmarkStart or index > bookmarkEnd
            data.linesOfCode[index] = escape(lineOfCode)
            continue
          if index == bookmarkEnd == bookmarkStart
            before = escape(lineOfCode.slice(0,data.startColumn - 1))
            inside = escape(lineOfCode.slice(data.startColumn - 1,data.endColumn - 1))
            after = escape(lineOfCode.slice(data.endColumn - 1))
            data.linesOfCode[index]= before + '<em class="violation-bookmark">' + inside + '</em>' + after
            continue
          if index == bookmarkStart
            before = escape(lineOfCode.slice(0,data.startColumn - 1))
            inside = escape(lineOfCode.slice(data.startColumn - 1))
            data.linesOfCode[index]= before + '<em class="violation-bookmark">' + inside + '</em>'
            continue
          if index == bookmarkEnd
            inside = escape(lineOfCode.slice(0,data.endColumn - 1))
            after = escape(lineOfCode.slice(data.endColumn - 1))
            data.linesOfCode[index]= '<em class="violation-bookmark">' + inside + '</em>' + after
            continue
          data.linesOfCode[index]= '<em class="violation-bookmark">' + escape(lineOfCode) + '</em>'
      else
        for index in [0..data.linesOfCode.length-1]
          data.linesOfCode[index] = escape(data.linesOfCode[index])
      return data

    _renderFragment:()->
      @$el.find('table tbody').append(@codeTemplate(
        @_prepareLinesOfCode(@model.toJSON()),
        helpers: {
          lineNumber: (index, model)->
            return model.startLine + index
          highlight: (line, model)->
            return 'secondary-bookmark' if model.secondary
            return ''
          highlightLineNumber: (line, model)->
            line = line + model.startLine
            if line >= model.objectStartLine and line <= model.objectEndLine and model.secondary
              return 'bookmark-object secondary-bookmark'
            if line >= model.objectStartLine and line <= model.objectEndLine and !model.secondary # highlight all object
              return 'bookmark-object'
#            return 'bookmark-object' if (line + model.startLine) == model.objectStartLine # highlight first line
            return ''
        })
      )


      @$el.find('.additional-info').show() if @model.get('secondary')
      @$el.find('.show-more').hide() unless @model.canShowMore()
      return @$el

    _renderMissingFragment:()->
      @$el.find('table tbody').append(@noCodeTemplate());

    render:()->
      @model.fetch().done(()=>
          @$el.html(@template(@model.toJSON()))
          @_renderFragment()
      ).fail(()=>
        @$el.html(@template(@model.toJSON()))
        @$el.find('.show-more').hide()
        @_renderMissingFragment()
        console.error 'error', arguments
      )
      return @$el
  })

  return Viewer
