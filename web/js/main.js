//Template for the project-info

/*
This file is part of Copernicus
http://www.copernicus-computing.org/

Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published 
by the Free Software Foundation

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

*/



$.template('project-tasks','<li task-id = "${id}">${id}(${state})</li>')
$.template('project-info',"<h1>${id}</h1><br/>${state}<br/><ul>{{tmpl(reports.tasks) 'project-tasks' }}</ul>")


$(document).ready(function(){
	

	
	//TODO be able to update information once new projects are added
	
	var projects
	
	
	$('#project-list').live('click',function(event){
		
		var elem = $(event.target)
		
		if(elem.is("li")){
			
			$('#project-list li').removeClass('highlight')
			elem.addClass('highlight')
			projectId = elem.attr('project-id')
			
			//kind of a brute force way to do it
			for(var i = 0;i<projects.length;i++){
				if(projectId == projects[i].id)
					project = projects[i]				
			}
			
			htmlstr= ''
				
			$('#project-info').html($.tmpl("project-info",project))	
		}
			
		
	});
	
	
	$.ajax({
		url: 'copernicus',
		type: 'POST',
		data : {cmd:'list',type:"projects"},
		datatype:'json',
		//error: handleError(),								
		success: function(data){			
			var htmlstr = ''
			projects = data[0].message
			for(var i = 0; i<projects.length;i++)
				htmlstr += '<li project-id="'+projects[i].id+'">'+projects[i].id+'<li>'
						
			$('#project-list').html(htmlstr)
			
			//TODO save this response in a class object for easy retreival of information later			
		}		
	});
	
	
	function handleError(){
		console.log('an error occured');
		//TODO nice error handling
	}
	
//	var uploader = new AjaxUpload('file-uploader',{
//		action:'copernicus',
//		name:'job',
//		autoSubmit:false,						
//		onSubmit: function(){
//			console.log('submitting')
//			var data = {}
//			//get all input fields from the form 
//			inputs = $('#project-form form input[type!="file"]')
//			for (var i = 0;i<inputs.length;i++){
//				name = $(inputs[i]).attr('name')				
//				value = $(inputs[i]).val()				
//				data[name] = value 
//			}
//			
//					
//			this.setData(data)	
//			
//		}
//			
//	});
	
	$('#submit-project').click(function(event){
		uploader.submit()
		return false
		
	})
	
	
	//uploader.submit action to trigger when we have created a submit button for the whole form
		
	

	
});
