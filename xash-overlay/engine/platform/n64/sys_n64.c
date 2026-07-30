/*
 * sys_n64.c - Nintendo 64/libdragon platform bring-up for Xash3D FWGS
 * Xash64 r14: real engine-core bootstrap target.
 */
#include "platform/platform.h"

#include <libdragon.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define XASH64_BASEDIR "sd:/xash"
#define XASH64_REQUIRED_RAM (8u * 1024u * 1024u)

static qboolean n64_sdfs_mounted = false;

static void N64_Fatal( const char *message )
{
	fprintf( stderr, "Xash64 FATAL: %s\n", message );
	fflush( stderr );
	abort( );
}

void Platform_ShellExecute( const char *path, const char *parms )
{
	(void)parms;
	fprintf( stderr, "Xash64: shell execute unsupported: %s\n", path ? path : "(null)" );
}

void Platform_MessageBox( const char *title, const char *message, qboolean parentMainWindow )
{
	(void)parentMainWindow;
	fprintf( stderr, "Xash64 %s: %s\n", title ? title : "message", message ? message : "" );
}

void Platform_SetStatus( const char *status )
{
	(void)status;
}

qboolean Platform_DebuggerPresent( void )
{
	return false;
}

platform_orientation_t Platform_GetDisplayOrientation( void )
{
	return ORIENTATION_LANDSCAPE;
}

double Platform_DoubleTime( void )
{
	return (double)get_ticks_us( ) / 1000000.0;
}

void Platform_Sleep( int msec )
{
	if( msec > 0 )
		wait_ms( (unsigned long)msec );
}

void N64_Init( void )
{
	const size_t memory_size = get_memory_size( );

	timer_init( );
	joypad_init( );
	(void)debug_init_usblog( );
	(void)debug_init_emulog( );
	n64_sdfs_mounted = debug_init_sdfs( "sd:/", -1 ) ? true : false;

	fprintf( stderr, "\nXash64 r14 platform init\n" );
	fprintf( stderr, "RAM: %lu bytes\n", (unsigned long)memory_size );
	fprintf( stderr, "SD mount: %s\n", n64_sdfs_mounted ? "OK" : "FAILED" );

	if( memory_size < XASH64_REQUIRED_RAM )
		N64_Fatal( "Expansion Pak required (8 MiB RAM)." );
	if( !n64_sdfs_mounted )
		N64_Fatal( "Could not mount flashcart SD filesystem at sd:/" );

	if( chdir( XASH64_BASEDIR ) != 0 )
	{
		fprintf( stderr, "Xash64: chdir(%s) failed, errno=%d\n", XASH64_BASEDIR, errno );
		N64_Fatal( "Copy the prepared xash/ directory to the root of the SummerCart SD card." );
	}

	fprintf( stderr, "Xash64 base directory: %s\n", XASH64_BASEDIR );
	fprintf( stderr, "Handing off to the real Xash3D FWGS engine core...\n" );
	fflush( stderr );
}

void N64_Shutdown( void )
{
	if( n64_sdfs_mounted )
	{
		debug_close_sdfs( );
		n64_sdfs_mounted = false;
	}
}
