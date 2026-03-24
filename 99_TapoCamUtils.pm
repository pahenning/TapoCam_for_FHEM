#######################################################################################
#
# TapoCamUtils 
#
# Collection of various routines for Tapo security cameras
# Prof. Dr. Peter A. Henning
#
# $Id: TapoCamUtils.pm 2020-09- pahenning $
#
########################################################################################
#
#  This programm is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  The GNU General Public License can be found at
#  http://www.gnu.org/copyleft/gpl.html.
#  A copy is found in the textfile GPL.txt and important notices to the license
#  from the author is found in LICENSE.txt distributed with these scripts.
#
#  This script is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
########################################################################################

package main;

use strict;
use warnings;
use SetExtensions;
use Data::Dumper;
use JSON; 

sub TapoCamUtils_Initialize($$){

  my ($hash) = @_;

}

###############################################################################
#
# TapoCamHandler - called by FHEM, calling Python scripts
#
# parameters: TapoCam device name, event
#
###############################################################################

sub TapoCamHandler($$){
  my ($name,$event) = @_;
  
  my $hash = $defs{$name};
  return if(!$hash);
  my $res;
  my $val;
  my $cmd;
  
  #--
  if( $event =~ /^getPhoto$/){
    $res = qx(/opt/fhem/tapo/tapo_snapshot.sh);
    chomp($res);
    fhem("setreading $name snapshot $res");
    return
  #-- status update
  }elsif( $event eq "status_update" ){
    my $cmd = '/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_privacy.py; '
          . '/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_light.py status; '
          . '/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_alarm.py status; '
          . '/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_detection.py status; ';
         # . '/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_events.py events 300; ';
    system('/bin/sh', '-c', "($cmd) >/dev/null 2>&1 &");
    return
  } 
  #Log 1,"========> event $event";
  #-- privacy
  if( $event =~ /^privacy\s+(on|off)$/){
    $event = $1;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_privacy.py $event >/dev/null 2>&1 &");
    
  #-- light
  }elsif($event =~ /^(led|light)\s+(on|off)$/){
    $event = $1;
    $val = $2;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_light.py $event $val >/dev/null 2>&1 &");
  }elsif($event =~ /^light_(intensity|duration)\s+(\d+)$/){
    $event = $1;
    $val = $2;
    $event =~ s/duration/time/;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_light.py $event $val >/dev/null 2>&1 &");
  }elsif($event =~ /^light_night\s+(ir|white|auto)$/){
    $val = $1;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_light.py night $val >/dev/null 2>&1 &");
    
  #-- motor
  }elsif( $event =~ /^move(Left|Right|Up|Down)$/){
    $event = lc($1);
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_motor.py $event >/dev/null 2>&1 &");
  }elsif( $event =~ /^move(Left|Right|Up|Down)\s+(\d+)$/){
    $event = lc($1);
    $val = $2;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_motor.py $event $val >/dev/null 2>&1 &");
  }elsif( $event =~ /^(getPresets|calibrate)$/){
    $event = lc($1);
    $event =~ s/get//;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_motor.py $event >/dev/null 2>&1 &");
  }elsif( $event =~ /^preset_(goto|delete|save)\s+(\d+)$/){
    $event = $1;
    $val = $2 // "";
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_motor.py $event $val >/dev/null 2>&1 &");
  
  #-- detection
  }elsif( $event =~ /^detection_(motion|person|pet|tamper|vehicle|linecrossing)\s+(\d+)$/){
    $event = $1;
    $val = $2;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_detection.py $event $val >/dev/null 2>&1 &");
  
  #-- alarm
   }elsif($event =~ /^alarm\s+(on|off)$/){
    $val = $1;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_alarm.py $val >/dev/null 2>&1 &");
  }elsif( $event =~ /^alarm_(light|sound)\s+(on|off)$/){
    $event = $1;
    $val = $2;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_alarm.py $event $val >/dev/null 2>&1 &");
  }elsif( $event =~ /^alarm_(volume|duration)\s+(.+)$/){
    $event = $1;
    $val = $2;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_alarm.py $event $val >/dev/null 2>&1 &");
  
  #-- events
  }elsif($event =~ /^getEvents$/){
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_events.py events >/dev/null 2>&1 &");
    #fhem("deletereading $name event_dl.*");
  }elsif($event =~ /^getEvents\s+(\d+)$/){
    $val = $1;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_events.py events $val >/dev/null 2>&1 &");
    #fhem("deletereading $name event_dl.*");
  }elsif($event =~ /^getClip\s+(\d+)$/){
    $val = $1;
    system("/opt/fhem/tapo/.venv/bin/python3 /opt/fhem/tapo/tapo_control_download.py clip $val >/dev/null 2>&1 &");
    #fhem("deletereading $name event_dl.*");
  }
}


###############################################################################
#
# TapoReturnHandler - called by Python scripts
# 
# parameteters: TapoCam device name, command group, json data
#
###############################################################################
##### TODO: Fehlerprüfung vereinheitlichen und auslagern

sub TapoReturnHandler($$$){
  my ($name,$group,$json) = @_;
  
  my $hash = $defs{$name};
  return if(!$hash);
  
  #Log 1,"obtained return to $name from Tapo group $group. json-result = $json";
  
  #-- JSON-String nach Perl-Hash wandeln
  if(!defined($json) || $json eq "") {
    readingsSingleUpdate($hash, "error", "empty json", 1) if $hash;
    return;
  }
  my $data;
  eval {
    $data = decode_json($json);
  };
  if($@ || ref($data) ne "HASH") {
    readingsSingleUpdate($hash, "error", "invalid json for group $group", 1);
    return;
  }
  
  #-- privacy
  if( $group eq "privacy" ){
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result})
      && $data->{result} eq "error"){
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else {
      my $state = $data->{privacy} // "";
      readingsBulkUpdate($hash,"privacy",$state);
      readingsBulkUpdate($hash, "error", "");
      readingsBulkUpdate($hash, "state", "privacy $state");
    }
    readingsEndUpdate($hash,1);
    
  #-- light
  }elsif($group eq "light") {
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result})
      && $data->{result} eq "error"){
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else {
      readingsBulkUpdate($hash, "light",           $data->{status})      if defined $data->{status};
      readingsBulkUpdate($hash, "light_intensity", $data->{intensity})   if defined $data->{intensity};
      readingsBulkUpdate($hash, "light_duration",  $data->{time})        if defined $data->{time};
      readingsBulkUpdate($hash, "light_remain",    $data->{time_remain}) if defined $data->{time_remain};
      readingsBulkUpdate($hash, "light_night",     $data->{night})       if defined $data->{night};
      readingsBulkUpdate($hash, "led",             $data->{led})         if defined $data->{led};
      readingsBulkUpdate($hash, "error", "");
      readingsBulkUpdate($hash, "state", "light ok");
    } 
    readingsEndUpdate($hash, 1);
     
  #-- motor
  }elsif( $group eq "motor" ){
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result}) && $data->{result} eq "error") {
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else{
      my $action = $data->{action} // "";
      my $result = $data->{result} // "";
      my $motor_action = "";
      my $state = "";

      #-- motor_action zusammensetzen
      if($action =~ /^(left|right|up|down)$/) {
        my $value = $data->{value} // 0;
        $motor_action = "$action $value";
      }elsif($action =~ /^(goto|save|delete)$/) {
        my $preset = $data->{preset} // "";
        $motor_action = "$action $preset";
      }
      else {
        $motor_action = $action;
      }
      readingsBulkUpdate($hash, "motor_action", $motor_action);
      readingsBulkUpdate($hash, "motor_result", $result);
      $state = $motor_action || $result;

      #-- presets-Liste
      if($action eq "presets") {
        my $presets = $data->{presets};
        if(ref($presets) eq "HASH") {
          my @names = map { $presets->{$_} } sort { $a <=> $b } keys %{$presets};
          my $preset_list = join(",", @names);
          readingsBulkUpdate($hash, "motor_presets", $preset_list);
          $state = "presets: $preset_list";
        } else {
          readingsBulkUpdate($hash, "motor_presets", "");
          $state = "presets";
        }
      }
      readingsBulkUpdate($hash, "error", "");
      readingsBulkUpdate($hash, "state", $state);
    }
    readingsEndUpdate($hash, 1);
  
  #-- detection
  }elsif($group eq "detection") {
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result}) && $data->{result} eq "error") {
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else{
      #-- Fall 1: kompletter Status
      if(ref($data->{motion})       eq "HASH"
        || ref($data->{person})       eq "HASH"
        || ref($data->{vehicle})      eq "HASH"
        || ref($data->{pet})          eq "HASH"
        || ref($data->{tamper})       eq "HASH"
        || ref($data->{linecrossing}) eq "HASH") {
        foreach my $type (qw(motion person vehicle pet tamper linecrossing)) {
          next if ref($data->{$type}) ne "HASH";

          my $enabled = $data->{$type}{enabled};
          next if !defined $enabled;

          my $reading = "detection_$type";
          my $value;

          if($type eq "linecrossing") {
            $value = $enabled;
          } else {
            if($enabled eq "off") {
              $value = "off";
            } else {
              my $sens = $data->{$type}{sensitivity};
              $value = defined($sens) ? "on $sens" : "on";
            }
          }
          readingsBulkUpdate($hash, $reading, $value);
        }
        readingsBulkUpdate($hash, "error", "");
        readingsBulkUpdate($hash, "state", "detection status");

      #-- Fall 2: Rückgabe eines set-Befehls
      }elsif(defined $data->{action}) {
        my $action  = $data->{action} // "";
        my $enabled = $data->{enabled};
        my $value   = $data->{value};
        my $result  = $data->{result};
        my $reading = "detection_$action";
        my $onoff = defined($enabled) ? ($enabled ? "on" : "off") : "";

        if($action eq "linecrossing") {
          readingsBulkUpdate($hash, $reading, $onoff) if $onoff ne "";
        } else {
          my $reading_value;
          if($onoff eq "off") {
            $reading_value = "off";
          } else {
            $reading_value = "on";
            $reading_value .= " $value" if defined $value;
          }
          readingsBulkUpdate($hash, $reading, $reading_value) if $reading_value ne "";
        }
        my $state = $action;
        $state .= " $onoff" if $onoff ne "";
        $state .= " $value" if defined $value && $action ne "linecrossing" && $onoff eq "on";
        readingsBulkUpdate($hash, "error", "");
        readingsBulkUpdate($hash, "state", $state);
      }
    }
    readingsEndUpdate($hash, 1);
    
  #-- alarm
  }elsif($group eq "alarm") {
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result})
      && $data->{result} eq "error"){
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "alarm error: $msg");
    }else {
      readingsBulkUpdate($hash, "alarm",          $data->{status})   if defined $data->{status};
      readingsBulkUpdate($hash, "alarm_sound",    $data->{sound})    if defined $data->{sound};
      readingsBulkUpdate($hash, "alarm_light",    $data->{light})    if defined $data->{light};
      readingsBulkUpdate($hash, "alarm_duration", $data->{duration}) if defined $data->{duration};
      readingsBulkUpdate($hash, "alarm_volume",   $data->{volume})   if defined $data->{volume};
     readingsBulkUpdate($hash, "error", "");

      my $state = "";
      $state .= "alarm:$data->{status} " if defined $data->{status};
      $state .= "sound:$data->{sound} " if defined $data->{sound};
      $state .= "light:$data->{light} " if defined $data->{light};
      $state .= "vol:$data->{volume} " if defined $data->{volume};
      $state .= "dur:$data->{duration}" if defined $data->{duration};
      $state =~ s/\s+$//;
      readingsBulkUpdate($hash, "state", $state) if $state ne "";
    }
   readingsEndUpdate($hash, 1);

   #-- events
   }elsif( $group eq "events" ){
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result})
      && $data->{result} eq "error"){
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else {
      my $window = $data->{events_window} // "";
      my $start  = $data->{events_start}  // "";
      my $list   = $data->{events_list}   // "";

      readingsBulkUpdate($hash, "events_window", $window);
      readingsBulkUpdate($hash, "events_start",  $start);
      readingsBulkUpdate($hash, "events_list",   $list);
      readingsBulkUpdate($hash, "error", "");
      readingsBulkUpdate($hash, "state", "events updated");
      
    }
    readingsEndUpdate($hash,1);

  #-- clip download
  }elsif( $group eq "download" ){
    readingsBeginUpdate($hash);
    #-- Fehler-Rückgabe aus Python
    if(defined($data->{result})
      && $data->{result} eq "error"){
      my $msg = $data->{message} // "unknown error";
      readingsBulkUpdate($hash, "error", $msg);
      readingsBulkUpdate($hash, "state", "$group error: $msg");
    }else {
      my $eventnr   = $data->{event_number} // "";
      my $etype     = $data->{event_type}   // "";
      my $etime     = $data->{event_time}   // "";
      my $dfile     = $data->{download_file} // "";
      my $plink     = $data->{public_link}   // "";

      readingsBulkUpdate($hash, "event_dl", $dfile);
      readingsBulkUpdate($hash, "event_dl_nr", $eventnr);
      readingsBulkUpdate($hash, "event_dl_type", $etype);
      readingsBulkUpdate($hash, "event_dl_time", $etime);
      readingsBulkUpdate($hash, "event_dl_link", "http://192.168.0.94:8083/fhem/images/TapoClip.mp4?x=".int(rand(1000)));
      readingsBulkUpdate($hash, "error", "");
      readingsBulkUpdate($hash, "state", "new clip obtained");
    }
    readingsEndUpdate($hash,1);
  }else{
    Log 1,"[TapoReturnHandler] invalid group $group,\n".Dumper($data);
  }
}
  
