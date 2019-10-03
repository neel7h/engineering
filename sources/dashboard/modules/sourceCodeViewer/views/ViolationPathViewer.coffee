ViolationPathViewer = (facade, CodeFragmentViewer, models)->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  escape = (()->
    tagsToReplace = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;'
    }
    return (string) ->
      string.trim().replace(/[&<>]/g, (tag) ->
        tagsToReplace[tag] || tag;
      )
  )()

  CodeSample = backbone.View.extend({
    template:Handlebars.compile('<table class="path-object"><tbody>{{#each linesOfCode}}
          <tr><td class="line-number {{highlightLineNumber @index ../this}}" data-line-number="{{lineNumber @index ../this}}"></td>

          <td class="{{highlight @index ../this}}">{{#if ../hasCallLabel}}<em class="call-label">call</em>{{/if}}{{#if ../hasReturnLabel}}<em class="return-label">return</em>{{/if}}<code class="">{{{this}}}</code></td></tr>
        {{/each}}</tbody></table>
        {{#if viewFile}}<a href="source.html{{viewFile}}?startline={{objectStartLine}}&endline={{objectEndLine}}&issueType={{issueType this}}&highlightBookmark={{highlightBookmark}}&secondary={{secondary}}" target="_blank" title="{{t "View the whole file content in a separate window."}}" class="view-file-icon"></a>{{/if}}')


    initialize:(options)->
      @options = _.extend({spread:0},options)
      @model = new models.SourceCode(@options)

    _prepareLinesOfCode:(data)->
      data.hasCallLabel = @options.hasCallLabel
      bookmarkStart = data.objectStartLine - data.startLine
      bookmarkEnd = data.objectEndLine - data.startLine
      if data.highlightBookmark
        for index in [0..data.linesOfCode.length-1]
          lineOfCode = data.linesOfCode[index]
          if index < bookmarkStart or index > bookmarkEnd
            data.linesOfCode[index] = escape(lineOfCode)
            continue

          if index == bookmarkEnd == bookmarkStart
            data.startColumn = 1 unless data.startColumn?
            data.endColumn = lineOfCode.length + 1 unless data.endColumn?
            before = escape(lineOfCode.slice(0,data.startColumn - 1))
            inside = escape(lineOfCode.slice(data.startColumn - 1,data.endColumn - 1))
            after = escape(lineOfCode.slice(data.endColumn - 1))
            data.linesOfCode[index]= before + '<em class="violation-bookmark">' + inside + '</em>' + after
            continue
          if index == bookmarkStart
            data.startColumn = 1 unless data.startColumn?
            before = escape(lineOfCode.slice(0,data.startColumn - 1))
            inside = escape(lineOfCode.slice(data.startColumn - 1))
            data.linesOfCode[index]= before + '<em class="violation-bookmark">' + inside + '</em>'
            continue
          if index == bookmarkEnd
            data.endColumn = lineOfCode.length + 1 unless data.endColumn?
            inside = escape(lineOfCode.slice(0,data.endColumn - 1))
            after = escape(lineOfCode.slice(data.endColumn - 1))
            data.linesOfCode[index]= '<em class="violation-bookmark">' + inside + '</em>' + after
            continue
          data.linesOfCode[index]= '<em class="violation-bookmark">' + escape(lineOfCode) + '</em>'
      else
        for index in [0..data.linesOfCode.length-1]
          data.linesOfCode[index] = '<em class="not-a-bookmark">' + escape(data.linesOfCode[index]) + '</em>'
      return data

    _renderFragment:()->
      @$el.html(@template(
        @_prepareLinesOfCode(@model.toJSON()),
        helpers: {
          lineNumber: (index, model)->
            return model.startLine + index
          highlight: (line, model)->
            return ''
          highlightLineNumber: (line, model)->
            return '' unless model.highlightBookmark
            line = line + model.startLine
            if line >= model.objectStartLine and line <= model.objectEndLine
              return 'bookmark-object'
            #            return 'bookmark-object' if (line + model.startLine) == model.objectStartLine # highlight first line
            return ''
        })
      )
      return @$el

    render:()->
      @model.fetch().done(()=>
        @_renderFragment()
      ).fail(()=>
        console.error 'error', arguments
      )
      return @$el
  })

  PathObjectView = backbone.View.extend({
    className: 'path-object-block'
    template:Handlebars.compile('<h4>{{component.name}}</h4>
      <div class="code-block"></div>')

    initialize:(options)->
      @options = options

    render:()->
      @$el.html(@template(@options))

      $block = @$el.find('.code-block')
      for bookmark in @options.bookmarks
        bookmarkView = new CodeSample({
          endColumn: bookmark.endColumn
          endLine: bookmark.endLine
          highlightBookmark: bookmark.highlightBookmark
          startColumn: bookmark.startColumn
          startLine: bookmark.startLine
          href:bookmark.file.href
          componentId:@options.componentId
          hasCallLabel: bookmark.isCall
          hasReturnLabel: bookmark.isReturn
          currentSnapshotHref: facade.context.get('snapshot').get('href')
        })
        $block.append(bookmarkView.render())
      return @$el
  })

  SinglePathView = backbone.View.extend({
    className: 'code-viewer object-viewer'

    template:Handlebars.compile('<h3>{{t "Violation path"}}</h3><hr>
      <div class="source-code-fragment-details path-block"></div>')

    initialize:(options)->
      @violationDetails = options.violationDetails
      @pathDetail = options.pathDetail

    _processPaths:()->
      results = []
      current = null
      for i in [0...@pathDetail.length]
        pathNode = @pathDetail[i]
        nextPathNode = @pathDetail[i+1]

        if nextPathNode?
          levelDirection = pathNode.level - nextPathNode.level
          if levelDirection<0
            pathNode.codeFragment?.isCall = true
          else if levelDirection>0
            pathNode.codeFragment?.isReturn = true

        if current?.href != pathNode.component.href
          componentId = pathNode.component.href.split('/')[2]
          current = {
            href:pathNode.component.href
            component:pathNode.component
            bookmarks:[]
            componentId:componentId
          }
          results.push(current)
        current.bookmarks.push(pathNode.codeFragment)

      first = results[0]
      first.bookmarks[0].highlightBookmark = true
      last = results[results.length-1]
      last.bookmarks[last.bookmarks.length-1].highlightBookmark=true

      return results

    render:()->
      @$el.html(@template())
      $block = @$el.find('.source-code-fragment-details')
      for pathNode in @_processPaths()
        pathObjectView = new PathObjectView(pathNode)
        $block.append(pathObjectView.render())

      return @$el
  })

  Viewer = backbone.View.extend({
    className: 'code-viewer object-viewer'
    tagName: 'div'
    template: Handlebars.compile('<h2 class="source-code">{{t "Source code"}}</h2>
      <div class="source-code-fragment-group {{#if isCritical}}critical{{/if}}">
        <p class="code-fragment-status">{{t  "Code"}} {{assign this "code"}} {{t "and violation" }} {{assign this "violation"}} {{t "since the last snapshot analysis"}}</p>
        <div class="rule-name">{{violationDetails.rule.name}}</div>
      </div>
      <button class="more-paths">{{t "More violation paths"}}</button>
      <div class="source-code-fragment-details">
      <h4 class="violation-details">{{t "Violation details"}}</h4>
      <div class="source-code-fragment-group-violation {{#if isCritical}}critical{{/if}}">
         <p>{{t "Associated values to the selected object in violation for rule is unavailable."}}</p>
         <h4>{{t "Why is that an issue?"}}</h4>
         <pre>{{violationDetails.rule.rationale}}</pre>
          <button class="learn-more">{{t "Learn more"}}</button>
      </div></div>')

    events:
      'click .more-paths': 'showMoreViolationPath'
      'click .learn-more': 'showDocumentation'

    initialize: (options)->
      @violationDetails = options.violationDetails
      @pagination = options.pagination || 1
      @startPath = 0

    showDocumentation: ()->
      facade.bus.emit('leave:zoom')
      facade.bus.emit('display:documentation')

    _renderPaths:()->
      $pathViewContainer = @$el.find('.source-code-fragment-group')
      paths = @violationDetails.getFindings().values

      for i in[@startPath...Math.min(@startPath+@pagination,paths.length)]
        pathView = new SinglePathView({
          violationDetails: @violationDetails
          pathDetail: paths[i]
        })
        $pathViewContainer.append(pathView.render())

      if paths.length > @startPath+ @pagination
        @$el.find('.more-paths').show()
      else
        @$el.find('.more-paths').hide()

    showMoreViolationPath:()->
      @startPath = @startPath + @pagination
      @_renderPaths()

    render:()->
      @$el.html(@template({
        violationDetails:@violationDetails.toJSON()
        isCritical:@violationDetails.isCritical()
      }))
      @_renderPaths()
      return @$el
  })

  return Viewer
