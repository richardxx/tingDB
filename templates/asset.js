/**
 * Created by richardxx on 1/7/14.
 */

(function (a) {
    var m = a("#popup"), n = a("#popup2"), d = 0;
    a(function () {
        a(".small.special").on("open.bpopup", function () {
            alert("I'm special")
        });
        a("body").on("click", ".small", function () {
            var c = a(this).hasClass("pop1") ? m : n, h = a(".content"), j = a(this);
            if (a(this).hasClass("events"))c.bPopup({onOpen: function () {
                alert("onOpen fired")
            }, onClose: function () {
                alert("onClose fired")
            }}, function () {
                alert("Callback fired")
            }); else if (a(this).hasClass("random")) {
                var e = b(0, a(window).width() - 500), p = b(a(document).scrollTop(), a(document).scrollTop() + a(window).height() - 300), k = 3 == b(0, 4), l = b(0, 2), f = "fadeIn", g = 350;
                1 === l ? (f = "slideDown", g = 600) : 2 === l && (f = "slideIn", g = 500);
                c.bPopup({follow: k ? [!0, !0] : [!1, !1], position: !k ? [e, p] : ["auto", "auto"], opacity: "0." + b(1, 9), positionStyle: 25 == b(0, 50) ? "fixed" : "absolute", modal: 0 == b(0, 10) ? !1 : !0, modalClose: 0 == b(0, 5) ? !1 : !0, modalColor: "hsl(" + b(0, 360) + ",100%, 50%)", transition: f, speed: g})
            } else a(this).hasClass("x-content") ? c.bPopup({onOpen: function () {
                h.html(j.data("bpopup") || {})
            }, onClose: function () {
                h.empty()
            }}) : a(this).hasClass("multi") ? (d++, c = b(0, a(window).width() - 500), e = b(a(document).scrollTop(), a(document).scrollTop() + a(window).height() - 300), a('<div class="bMulti"><span class="button bClose close' + d + '"><span>X</span></span><p>' + d + '</p><a class="button small multi">Pop another up</a></div>').bPopup({closeClass: "close" + d, position: [c, e], follow: [!1, !1], onClose: function () {
                d--;
                a(this).remove()
            }})) : c.bPopup(j.data("bpopup") || {})
        })
    });
    var b = function (a, b) {
        return~~(Math.random() * (b - a + 1) + a)
    }
})(jQuery);
/*TWITTER*/
!function (d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (!d.getElementById(id)) {
        js = d.createElement(s);
        js.id = id;
        js.src = "//platform.twitter.com/widgets.js";
        fjs.parentNode.insertBefore(js, fjs);
    }
}(document, "script", "twitter-wjs");
/*PLUSONE*/
(function () {
    var po = document.createElement('script');
    po.type = 'text/javascript';
    po.async = true;
    po.src = 'https://apis.google.com/js/plusone.js';
    var s = document.getElementsByTagName('script')[0];
    s.parentNode.insertBefore(po, s);
})();
/*BIG BROTHER*/
var _gaq = [
    ['_setAccount', 'UA-528252-3'],
    ['_trackPageview']
];
(function (d, t) {
    var g = d.createElement(t), s = d.getElementsByTagName(t)[0];
    g.src = ('https:' == location.protocol ? '//ssl' : '//www') + '.google-analytics.com/ga.js';
    s.parentNode.insertBefore(g, s)
}(document, 'script'));