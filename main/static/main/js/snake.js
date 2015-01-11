// Generated by CoffeeScript 1.8.0
(function() {
  var buildComment, commentFormTemplate, commentTemplate, displayError, empty, getCsrfCookie, insertComment, markAsNewComment, resetInputBorderColorOnClick, rumble, saveComment, updateCommentCount;

  commentTemplate = '<div class="comment-box" style="display: none">' + '    <div class="comment-internals">' + '        <div>' + '            <p class="comment-author">author</p>' + '            <p class="comment-body">body</p>' + '        </div>' + '        <div>' + '            <p style="text-align: right">' + '                <a href="javascript:void(0)" class="reply">Reply</a>' + '            </p>' + '        </div>' + '    </div>' + '</div>';

  commentFormTemplate = '<div class="new-comment">' + '    <div class="comment-form">' + '        <p class="alert alert-warning" style="display: none">Something\'s gone wrong, Jim. Please try again in a bit.</p>' + '        <textarea placeholder="Leave a comment" class="comment-field"></textarea>' + '        <div class="comment-slider" style="display: none">' + '            <button class="save-button form-item">Save</button>' + '            <input type="text" placeholder="Name" class="name-field form-item">' + '        </div>' + '    </div>' + '</div>';

  empty = function(x) {
    return x.val().length === 0;
  };

  rumble = function(element, amount) {
    if (amount === 0) {
      return;
    }
    element.css('position', 'relative');
    element.animate({
      'left': '1px'
    }, 50).animate({
      'left': '0px'
    }, 50);
    return rumble(element, amount - 1);
  };

  displayError = function(element) {
    element.css('border-color', '#F44336');
    return rumble(element, 4);
  };

  buildComment = function(data) {
    var commentBox;
    commentBox = $(commentTemplate);
    commentBox.attr('id', data.comment_id);
    commentBox.find('p.comment-author').text(data.name);
    commentBox.find('p.comment-body').text(data.body);
    commentBox.find('a.reply').hide();
    return commentBox;
  };

  markAsNewComment = function($newComment) {
    return 1234;
  };

  insertComment = function(element, data) {
    var commentBox, newComment, parent;
    parent = element.parents('.comment-box:first');
    commentBox = buildComment(data);
    if (parent.length !== 0) {
      parent.find('.comment-internals:first').after(commentBox.prop('outerHTML'));
    } else {
      $('.root-comment').prepend(commentBox.prop('outerHTML'));
    }
    newComment = $('#' + data.comment_id);
    newComment.next().css({
      'margin-left': 0
    });
    return newComment.fadeIn().find('.comment-author').css('color', '#9f5512');
  };

  updateCommentCount = function() {
    var $commentNumber, currentParsedNumber;
    $commentNumber = $('#total-comments');
    currentParsedNumber = parseInt($commentNumber.text());
    return $commentNumber.text(currentParsedNumber + 1);
  };

  saveComment = function(element) {
    var parent, parentId;
    parent = element.parents('.comment-box');
    if (parent.length === 0) {
      parentId = null;
    } else {
      parentId = parent.attr('id');
    }
    return new Promise(function(resolve, reject) {
      return $.ajax('./storecomment/', {
        type: 'POST',
        data: {
          'parent_id': parentId,
          'body': element.parent().prev('textarea').val(),
          'name': element.next('.name-field').val()
        },
        xhrFields: {
          withCredentials: true
        }
      }).done(function(data) {
        console.log("success!");
        return resolve(data);
      }).fail(function(err) {
        return reject(err);
      });
    });
  };

  getCsrfCookie = function() {
    var cookie, _i, _len, _ref, _results;
    _ref = document.cookie.split(';');
    _results = [];
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      cookie = _ref[_i];
      if (cookie.indexOf('csrftoken') > -1) {
        _results.push($.trim(cookie.split('=')[1]));
      }
    }
    return _results;
  };

  resetInputBorderColorOnClick = function(defaultBorderColor) {
    return $(document).on('click', '.comment-field, .name-field', function(evt) {
      return $(this).css('border-color', defaultBorderColor);
    });
  };

  jQuery(function($) {
    var commentBox, defaultBorderColor;
    commentBox = $('.comment-field');
    defaultBorderColor = commentBox.css('border-color');
    resetInputBorderColorOnClick(defaultBorderColor);
    commentBox.on('click', function() {
      return $(this).animate({
        'height': '120px'
      }, 'slow').unbind().next('.comment-slider').slideDown();
    });
    $(document).on('click', '.save-button', function(evt) {
      var comment, name;
      evt.preventDefault();
      comment = $(this).parents(".new-comment").find('textarea');
      name = $(this).next('.name-field');
      if (empty(comment)) {
        displayError(comment);
      }
      if (empty(name)) {
        displayError(name);
      }
      if (!empty(comment) && !empty(name)) {
        return saveComment($(this)).then((function(res) {
          console.log(res);
          insertComment($(evt.target), res);
          updateCommentCount();
          return setTimeout((function() {
            return $(evt.target).parents(".new-comment").slideUp();
          }), 500);
        }), (function() {
          var error;
          error = $(evt.target).parents('div.comment-form').find('p.alert');
          error.css('display', 'block');
          return rumble(error, 2);
        }));
      }
    });
    return $('.comment-box .reply').on('click', function() {
      var child, parent, parentAuthor;
      parent = $(this).parents('.comment-internals');
      parentAuthor = parent.find('p.comment-author');
      child = $(commentFormTemplate);
      child.appendTo(parent);
      child.find('.comment-field, .name-field').css('border-color', defaultBorderColor);
      child.find('textarea').attr('placeholder', 'replying to ' + parentAuthor.text()).animate({
        'height': '120px'
      }, 'slow');
      child.find('.comment-slider').slideDown();
      return $(this).hide();
    });
  });

}).call(this);

//# sourceMappingURL=snake.js.map
