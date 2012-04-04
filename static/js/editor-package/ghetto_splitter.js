;(function(window, document, undefined){
	window.GhettoSplitter = {
		makeSplitter: function($dragHandle, options){
			return function(){
				var dragging = false;

				$dragHandle
				.mousedown(function(evt){ // DragStart
					if(dragging === true) return;
					dragging = true;
					if(options && typeof(options.onDragStart) === 'function') options.onDragStart.call($dragHandle, evt);
					return false;
				});

				$(document)
				.mousemove(function(evt){ // Drag
					if(dragging === false) return;
					if(options && typeof(options.onDrag) === 'function') options.onDrag.call($dragHandle, evt);
					return false;
				})
				.mouseup(function(evt){ // DragStop
					if(dragging === false) return;
					dragging = false;
					if(options && typeof(options.onDragStop) === 'function') options.onDragStop.call($dragHandle, evt);
					return false;
				});
			}();
		}
	};
}(window, document));
