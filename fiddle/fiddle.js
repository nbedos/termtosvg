var price_chart   = document.getElementsByTagName('svg')[0];
var screen   = price_chart.getElementsByTagName('svg')[0];
var pt    = price_chart.createSVGPoint();

console.log(price_chart)
console.log(screen)

function mx(evt){
        pt.x = evt.clientX;
        return pt.matrixTransform(price_chart.getScreenCTM().inverse());
}

// HTML elements
var slider_1  = document.querySelector('#slider_1');
console.log(slider_1)

var dragging = false;
slider_1.addEventListener('mousedown',function(evt){
        price_chart.pauseAnimations()
        var offset = mx(evt);
        dragging = true;
        offset.x = slider_1.x.baseVal.value - offset.x;
        var move = function(evt){
                var now = mx(evt);
                //var x = offset.x + now.x;
                var x = now.x;
                var limitLower = 0;
                var limitUpper = 300;
                console.log(evt)
                if ( x < limitLower || x > limitUpper ) {
                    return;
                }
                //slider_1.x.baseVal.value = x;
                //x = Math.abs(x)*scale;
                price_chart.setCurrentTime(10.0 * x / 300.0)
        };

        price_chart.addEventListener('mousemove',move,false);
        document.documentElement.addEventListener('mouseup',function(){
                dragging = false;
                price_chart.unpauseAnimations()
                price_chart.removeEventListener('mousemove',move,false);
        },false);
},false);
