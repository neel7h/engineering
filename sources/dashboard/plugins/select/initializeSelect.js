(function(W) {
    Window.initializeSelect = function (theme, placeholderValue, tagValue, actionValue, action) {
        var currentSelector = '';
        return this.each (function () {
            var _this      = $(this);
            var optionList = [];

            // INSERTION OF PRETTY DISPLAYED SELECTOR
            var _insertPrettySelector = function () {
                // Use of pretty selector can not be done with standard input. Create one holder which will contain original select + pretty display select.
                selectOnly = action == 'reset' ? "selectOnly": "";
                _this.wrap('<div class="select-holder '+ selectOnly +'"></div>');
                var holder = _this.parent();

                // Prepare all span elements as selectable option
                var optionString   = '';
                var optionValue    = '';
                var optionSelected = '';
                _this.find('option').each (function (_key, optionElement) {
                    optionElement = $(optionElement);
                    optionValue   = optionElement.val();
                    if (optionValue !== '') {
                        optionSelected = optionElement.attr('selected');
                        optionSelected = optionSelected === 'selected'?' selected':'';
                        if ((optionElement.text()) == tagValue ||  optionValue == localStorage.getItem("language") ||optionElement.text() == actionValue ) {
                            optionString   = optionString + '<span class="option' + optionSelected +" "+ theme + '" data="' + optionValue + '">' + optionElement.text() + '</span>';
                        }
                        else {
                            optionString   = optionString + '<span class="option' + optionSelected + '" data="' + optionValue + '">' + optionElement.text() + '</span>';
                        }
                        optionList[optionValue] = optionElement.text();
                    }
                });

                // Insert the selector menu
                holder.prepend('<div class="selector">' + optionString + '</div>').addClass('noselect');
                if(action == 'reset'){
                    holder.find('.selector').css({'overflow-y': 'scroll'})
                }
                // Insert the selector display
                var selectPrettyDisplay = __getSelectPrettyDisplay(optionList[_this.val()], placeholderValue);
                holder.prepend(selectPrettyDisplay);

                // Declare Callbacks
                $('.option', holder).click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    _getSelectedOptions(e);
                    __selectItem($(e.currentTarget), holder);
                    _getAllSelectedActionOptions();
                    });
                $('.input-select', holder).first().click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    __toggleMenu(holder);
                });
            }

            var __getSelectPrettyDisplay = function (currentValue, placeholderValue) {
                if (currentValue === undefined) {
                    return '<div class="input-select no-value"><span>' + placeholderValue + '</span></div>';
                } else {
                    return '<div class="input-select"><span>' + currentValue + '</span></div>';
                }
            }

            var _getSelectedOptions = function (e){
                var currentTarget = e.currentTarget;
                if($('.selected-priority').val() === currentTarget.textContent.toLowerCase() || $('.selected-actions').val() === currentTarget.textContent && $('.modal-group textarea').val() === $('.modal-group #comment').val().trim() || localStorage.getItem("language") == currentTarget.attributes['data'].value){
                    $('#select-holder').removeClass('show');
                    $('#perform').addClass('btn-disable')
                } else {
                    $('#perform').removeClass('btn-disable')
                }
            }

            var _getAllSelectedActionOptions = function (){
                if ($('.select-holder').hasClass('selected-actions')){
                    if (!$('.selected-priority').find('.selected').text() && $('.selected-actions').find('.selected').text()){
                        $('#select-holder').removeClass('show');
                        $('#perform').addClass('btn-disable');
                    }else if ($('.selected-priority').val() === $('.selected-priority').find('.selected').text().toLowerCase() && ($('.modal-group textarea').val() === "" || $('.modal-group textarea').val() == $('.modal-group #comment').val().trim())  && ($('.selected-actions').val() === $('.selected-actions').find('.selected').text())){
                        $('#select-holder').removeClass('show');
                        $('#perform').addClass('btn-disable');
                    }else if ($('.selected-priority').val() !==  $('.selected-priority').find('.selected').text().toLowerCase() || $('.selected-actions').val() !== $('.selected-actions').find('.selected').text() || ($('.modal-group textarea').val() !== "" || $('.modal-group textarea').val() !== $('.modal-group #comment').val().trim())) {
                        $('#perform').removeClass('btn-disable')
                    }
                }
            }

            var __toggleMenu = function (selectHolder) {
                if (selectHolder.hasClass('show')) {
                    $('.selector', selectHolder).first().animate({'opacity':'0'}, 100, function () {
                        selectHolder.removeClass('show');
                        currentSelector = '';
                    }).removeClass('no-offset');
                } else {
                    if (currentSelector !== '') {
                        var currentSelector_ = currentSelector;
                        currentSelector = '';
                        __toggleMenu(currentSelector_);
                    }
                    var menu = $('.selector', selectHolder);
                    ___setMenuPosition(selectHolder, menu);
                    menu.first().animate({'opacity':'1'}, 100).addClass('no-offset');
                    var select = $('.modal-container .select-holder .selector');
                    var option = $('.modal-container .select-holder .selector .selected');
                    if(option.offset()){
                        select.scrollTop(select.scrollTop() + (option.offset().top - select.offset().top));
                    }
                    $('body').bind('click', function(event){
                        $('body').unbind('click');
                        __toggleMenu(selectHolder);
                        selectHolder.removeClass('show');
                    });
                    currentSelector = selectHolder;
                }
                if ($('.selected-priority').hasClass('show')){
                    $('.selected-actions').removeClass('show');
                }
                else if($('.selected-actions').hasClass('show')){$('.selected-prioriry').removeClass('show')}
            }

            var __selectItem = function (option, selectHolder) {
                $('.option', selectHolder).removeClass('selected '+ theme);
                option.addClass('selected '+ theme);

                var selectElement = $('select', selectHolder).first();
                var newValue      = option.attr('data');
                selectElement.val(newValue);

                __toggleMenu(selectHolder);

                var inputSelect = $('.input-select', selectHolder).first();
                var textHolder  = inputSelect.find('span').first();
                var currentWidth = textHolder.width();
                inputSelect.removeClass('no-value');
                textHolder.text(optionList[newValue]);
                var newWidth = textHolder.width();
                textHolder.css({'width':currentWidth + 'px'});
                textHolder.animate({'width':newWidth}, 100, function () {
                    textHolder.css({'width':''});
                });


                if ("createEvent" in document) {
                    var evt = document.createEvent("HTMLEvents");
                    evt.initEvent("change", false, true);
                    selectElement.get(0).dispatchEvent(evt);
                } else {
                    selectElement.get(0).fireEvent("onchange");
                }
            }

            var ___setMenuPosition = function (holder, menu) {
                // Display & reset positions
                holder.addClass('show '+ theme).removeClass('right');
                // Handle right position if menu is out of the window
                if (menu.width() + menu.offset().left >= $(window).width()) {
                    holder.addClass('right');
                }
            }


            // SELECT INITIALIZATION
            _insertPrettySelector ();
        });
    }
})(window);