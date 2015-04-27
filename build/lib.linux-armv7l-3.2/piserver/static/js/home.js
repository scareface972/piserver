/**
 * Created by benjamin on 01/05/14.
 */

if (typeof jQuery === 'undefined') { throw new Error('This JavaScript requires jQuery') }

/**
 * Starting App
 */
$(document).ready(function() {
    var h = new Horloge(true);
    var w = new Weather();
    var s = new Temps();
});

/**
 * Horloge
 */
var Horloge = function(withSeconds) {
    this.withSeconds = withSeconds;
    this.setup();
    this.update();
    var t = this;
    this.timer = setInterval(function(){t.update();}, 1000);
};
Horloge.MONTHS  = [ "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre" ];
Horloge.DAYS    = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
Horloge.prototype.setup = function() {
    this.date = $('#date');
    this.hours = $('#hours');
    this.min = $('#min');
    this.sec = $('#sec');
    if (!this.withSeconds) {
        $("#pointSec").hide();
        this.sec.hide();
    }
}
Horloge.prototype.update = function() {
    var now = new Date();
    var date = Horloge.DAYS[now.getDay()].toUpperCase() + ' ';
    date += now.getDate() + (now.getDate() == 1 ? 'er' : '') + ' ';
    date += Horloge.MONTHS[now.getMonth()].toUpperCase() + ' ';
    date += now.getFullYear();
    this.date.html(date);
    this.hours.html(( now.getHours() < 10 ? "0" : "" ) + now.getHours());
    this.min.html(( now.getMinutes() < 10 ? "0" : "" ) + now.getMinutes());
    if (this.withSeconds) this.sec.html(( now.getSeconds() < 10 ? "0" : "" ) + now.getSeconds());
}

/**
 * Weather
 */
var Weather = function() {
    this.params = {
        'q':'Bordeaux,France',
        'units':'metric',
        'lang':'fr'
    };
    this.updateCurrent();
    this.updateForecast();
    var t = this;
    this.timer = setInterval(function(){
        t.updateCurrent();
        t.updateForecast();
    }, 60000);
}
Weather.ICONS = {
    '01d':'wi-day-sunny',
    '02d':'wi-day-cloudy',
    '03d':'wi-cloudy',
    '04d':'wi-cloudy-windy',
    '09d':'wi-showers',
    '10d':'wi-rain',
    '11d':'wi-thunderstorm',
    '13d':'wi-snow',
    '50d':'wi-fog',
    '01n':'wi-night-clear',
    '02n':'wi-night-cloudy',
    '03n':'wi-night-cloudy',
    '04n':'wi-night-cloudy',
    '09n':'wi-night-showers',
    '10n':'wi-night-rain',
    '11n':'wi-night-thunderstorm',
    '13n':'wi-night-snow',
    '50n':'wi-night-alt-cloudy-windy'
}
Weather.DAYSABBR = ['Di.','Lu.','Ma.','Me.','Je.','Ve.','Sa.'];
Weather.prototype.updateCurrent = function() {
    $.getJSON('http://api.openweathermap.org/data/2.5/weather', this.params, function(json, textStatus) {

        var iconClass = Weather.ICONS[json.weather[0].icon];
        var icon = $('<span/>').addClass('icon').addClass('dimmed').addClass('wi').addClass(iconClass);
        var iconString = icon.wrapAll('<div></div>').parent().html();
        $('#icon').updateWithText(iconString);

        $('#city').updateWithText(json.name);

        var temp = roundVal(json.main.temp);
        var temp_min = roundVal(json.main.temp_min);
        var temp_max = roundVal(json.main.temp_max);
        var tempString = temp+'&deg;';
        if (temp != temp_min && temp_min != temp_max)
            tempString += '<div class="xdimmed">min:' + temp_min+'&deg; - max:' + temp_max+'&deg;</div>';
        $('#temp').updateWithText(tempString);

        var wind = roundVal(json.wind.speed);
        var now = new Date();
        var sunrise = new Date(json.sys.sunrise*1000).toTimeString().substring(0,5);
        var sunset = new Date(json.sys.sunset*1000).toTimeString().substring(0,5);
        //var str = '<span class="wi wi-strong-wind xdimmed"></span> ' + '<span class="xdimmed">' + kmh2beaufort(wind) + '</span> ' ;
        var str = '<span class="wi wi-strong-wind"></span> ' + wind + ' <span style="text-transform: lowercase">km/h</span>';
        str += '&nbsp;&nbsp;&nbsp;<span class="wi wi-sunrise"></span> ' + sunrise;
        str += '&nbsp;&nbsp;&nbsp;<span class="wi wi-sunset"></span> ' + sunset;
        $('#windsun').updateWithText(str);
    });
}
Weather.prototype.updateForecast = function() {
    $.getJSON('http://api.openweathermap.org/data/2.5/forecast', this.params, function(json, textStatus) {
        var forecastData = {};
        for (var i in json.list) {
            var forecast = json.list[i];
            var dateKey  = forecast.dt_txt.substring(0, 10);
            if (forecastData[dateKey] == undefined) {
                forecastData[dateKey] = {
                    'timestamp':forecast.dt * 1000,
                    'temp_min':forecast.main.temp,
                    'temp_max':forecast.main.temp
                };
            } else {
                forecastData[dateKey]['temp_min'] = (forecast.main.temp < forecastData[dateKey]['temp_min']) ? forecast.main.temp : forecastData[dateKey]['temp_min'];
                forecastData[dateKey]['temp_max'] = (forecast.main.temp > forecastData[dateKey]['temp_max']) ? forecast.main.temp : forecastData[dateKey]['temp_max'];
            }

        }
        var forecastTable = $('<table />').addClass('forecast-table');
        var opacity = 1;
        var row = $('<tr />').css('opacity', opacity);
        row.append($('<td/>'));
        row.append($('<td/>').addClass('temp-max').html('<small>max.</small>'));
        row.append($('<td/>').addClass('temp-min').html('<small>min.</small>'));
        forecastTable.append(row);
        for (var i in forecastData) {
            var forecast = forecastData[i];
            var dt = new Date(forecast.timestamp);
            var row = $('<tr />').css('opacity', opacity);
            row.append($('<td/>').addClass('day').html(Weather.DAYSABBR[dt.getDay()]));
            row.append($('<td/>').addClass('temp-max').html(roundVal(forecast.temp_max)+'&deg;'));
            row.append($('<td/>').addClass('temp-min').html(roundVal(forecast.temp_min)+'&deg;'));
            forecastTable.append(row);
            opacity -= 0.155;
        }
        $('#forecast').updateWithText(forecastTable);
    });
}

/**
 * Calendar
 */
var Calendar = function() {

}
Calendar.prototype.load = function() {
    /*
    new ical_parser("calendar.php", function(cal){
    events = cal.getEvents();
    eventList = [];

    for (var i in events) {
        var e = events[i];
        for (var key in e) {
            var value = e[key];
            var seperator = key.search(';');
            if (seperator >= 0) {
                var mainKey = key.substring(0,seperator);
                var subKey = key.substring(seperator+1);

                var dt;
                if (subKey == 'VALUE=DATE') {
                    //date
                    dt = new Date(value.substring(0,4), value.substring(4,6) - 1, value.substring(6,8));
                } else {
                    //time
                    dt = new Date(value.substring(0,4), value.substring(4,6) - 1, value.substring(6,8), value.substring(9,11), value.substring(11,13), value.substring(13,15));
                }

                if (mainKey == 'DTSTART') e.startDate = dt; 
                if (mainKey == 'DTEND') e.endDate = dt; 
            }
        }

        var now = new Date();
        var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        var days = moment(e.startDate).diff(moment(today), 'days');

        //only add fututre events
        if (days >= 0) {
            eventList.push({'description':e.SUMMARY,'days':days});
        }
    };
    eventList.sort(function(a,b){return a.days-b.days});
    */
}
Calendar.prototype.update = function() {

}

var Temps = function() {
    this.update();
    var t = this;
    this.timer = setInterval(function(){t.update();}, 30*60000);
}
Temps.prototype.update = function() {
    $.getJSON('/exec/temp/all', this.params, function(json, textStatus) {
        //console.log('json: ' + json);
        //console.log('textStatus: ' + textStatus);
        if (textStatus == 'success') {
            console.log('temp: ' + json['temp_c'] + '°C');
            console.log('humidity: ' + json['humidity'] + '%');
            $('#home_temp').html(json['temp_c'] + '°C / ' + json['humidity'] + '% d\'humidité');
        }
    });
};

var states = new EventSource('/states');
states.addEventListener('message', function(e) {
    //console.log('data: ' + e.data);
    var result = JSON.parse(e.data);
    if (result.success) {
        for (i=0; i<result.states.length; i++) {
            var elt = $('#'+result.states[i].name)[0];
            //console.log('state changed: ' + result.states[i].name + ' > ' + result.states[i].state + " " + elt.className)
            if (result.states[i].state && elt.className == 'circle-unchecked')
                $('#'+result.states[i].name).attr('class', 'circle-checked');
            else if (!result.states[i].state && elt.className == 'circle-checked')
                $('#'+result.states[i].name).attr('class', 'circle-unchecked');
        }
    }
}, false);

function check(element) {
    var elt = $(element)[0];
    var action = 'off';
    var className = elt.className.split('-').pop();
    //console.log(className);
    if (className == 'checked') className = 'unchecked';
    else { action = 'on'; className = 'checked'; }
    $(element).attr('class', 'circle-' + className);
    $.get('/exec/' + elt.id + '/' + action);
}

function roundVal(temp) {
    return Math.round(temp * 10) / 10;
}

function kmh2beaufort(kmh) {
    var speeds = [1, 5, 11, 19, 28, 38, 49, 61, 74, 88, 102, 117, 1000];
    for (var beaufort in speeds) {
        var speed = speeds[beaufort];
        if (speed > kmh) {
            return beaufort;
        }
    }
    return 12;
}

jQuery.fn.updateWithText = function(text, speed) {
    if (speed == undefined) speed = 1000;
    var dummy = $('<div/>').html(text);
    if ($(this).html() != dummy.html()) {
    	$(this).html(text);
    }
}