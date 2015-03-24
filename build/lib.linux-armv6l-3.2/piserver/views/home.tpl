<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Mirroir</title>
    <link href="/static/css/roboto.css" rel="stylesheet">
    <link href="/static/css/weather-icons.css" rel="stylesheet">
    <link href="/static/css/home.css" rel="stylesheet">
</head>
<body>

<div class="container">

    <div id="clock">
        <div id="date">Jeudi 1er Mai 2014</div>
        <ul>
            <li id="hours"></li>
            <li id="point">:</li>
            <li id="min"></li>
            <li id="pointSec">:</li>
            <li id="sec"></li>
        </ul>
    </div>

    <div id="weather">
        <div id="icon"></div>
        <div id="city"></div>
        <div id="temp"></div>
        <div id="windsun" class="xdimmed"></div>
    </div>

    <div id="domotic">
        %group = None
        %colcount = 3
        %cnt = 0
        <table>
            <tr>
                <td colspan="{{colcount}}" class="title">Domicile</td>
            </tr>
            <tr>
                <td colspan="{{colcount}}" class="label" id="home_temp">Chargement...</td>
            </tr>
            %for module in switchers:
            %   checked = 'checked' if module.state else 'unchecked'
            %   if cnt%colcount==0:
                    <tr class="switch">
            %   end
            %   cnt += 1
                    <td class="label">{{module.name}}</td>
                    <td><div id="{{module.name}}" class="circle-{{checked}}" onclick="check(this);">&nbsp;</div></td>
            %   if cnt%colcount==0:
                    </tr>
            %   end
            %end
        </table>
    </div>

    <div id="forecast"></div>

</div>

<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
<!-- Include all compiled plugins (below), or include individual files as needed -->
<script src="/static/js/home.js"></script>
</body>
</html>