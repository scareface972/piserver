%from modules import chacom
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" type="text/css" href="/static/css/{{style}}/global.css">
<link rel="stylesheet" type="text/css" href="/static/css/{{style}}/switch.css">
<meta name="viewport" content="width=device-width"/>
</head>
<body>
<h1>Maison</h1>
<table border="0">
%group = None
%for module in switchers:
%	checked = 'checked' if module.state else ''
	<tr>
	<td class="label">{{module.name}}:</td>
	<td><div class="onoffswitch">
	    <input type="checkbox" name="{{module.name}}" class="onoffswitch-checkbox" id="{{module.name}}" onchange="setup('{{module.name}}', this.checked ? 'on' : 'off')" {{checked}}>
	    <label class="onoffswitch-label" for="{{module.name}}">
	        <div class="onoffswitch-inner">
	            <div class="onoffswitch-active"><div class="onoffswitch-switch">ON</div></div>
	            <div class="onoffswitch-inactive"><div class="onoffswitch-switch">OFF</div></div>
	        </div>
	    </label>
	</div></td>
	<td>
%if isinstance(module, chacom.Switch):
	CHACOM
%end
	</td>
	</tr>
%end
</table>
<!-- 
<h1>Recherche de commande(s)</h1>
<form method="post" onsubmit="search(this.qry.value); return false;">
<input type="text" name="qry" size="40" /><br/>
<input type="submit" value="Rechercher">
</form>
<div id="result"></div>
-->
<script src="/static/js/controls.js"></script>
</body>
</html>
