#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <dirent.h>


void feed_device(const char* dev, FILE* log_fd) {
    FILE *fd = fopen(dev, "w+");
    if (fd != NULL) {
        fprintf(log_fd, "feeding device %s\n", dev);
        fprintf(fd, "%s\n", dev);
        fclose(fd);
    } else {
        fprintf(log_fd, "unable to open device %s\n", dev);
    }
}

void print_ls(const char* ls_dir, FILE* fd) {
    DIR *d;
    struct dirent *dir;
    d = opendir(ls_dir);
    if (d) {
        while ((dir = readdir(d)) != NULL) {
            fprintf(fd, "%s\n", dir->d_name);
        }
        closedir(d);
    }
    fprintf(fd, "\n");
}

int main()
{
    FILE *log_fd = fopen("/dev/ttyprintk", "w");
    if (log_fd <= 0) {
        reboot(RB_AUTOBOOT);
        return 0;
    }

    feed_device("/dev/tty", log_fd);
    feed_device("/dev/console", log_fd);
    feed_device("/dev/tty0", log_fd);
    feed_device("/dev/tty1", log_fd);
    feed_device("/dev/ttyS0", log_fd);
    feed_device("/dev/ttyS1", log_fd);
    feed_device("/dev/ttyprintk", log_fd);
    feed_device("/dev/vtcon0", log_fd);
    feed_device("/dev/fbcon", log_fd);

    fprintf(log_fd, "remounting rootfs\n");

    print_ls("/dev", log_fd);

    if (mount("", "/", "", MS_REMOUNT, NULL) < 0) {
        fprintf(log_fd, "remount root failed\n");
        while(1) { sleep(1); }
    } else {
        fprintf(log_fd, "remount root ok\n");
    }

    int init_fd = open("/dev/ttyprintk", O_WRONLY);
    if (init_fd <= 0) {
        fprintf(log_fd, "opening init_log failed\n");
        while(1) { sleep(1); }
    } else {
        fprintf(log_fd, "init_log opened\n");
    }

    dup2(init_fd, STDOUT_FILENO);
    dup2(init_fd, STDERR_FILENO);
    execve("/sbin/init", NULL, NULL);

    while(1) { sleep(60); }

    //FILE *log_f = fopen("/var/log/dbgstub", "w+");
    //if (log_f <= 0) {
    //    return 1;
    //}

    /*feed_device("/dev/tty", log_f);
    feed_device("/dev/console", log_f);
    feed_device("/dev/tty0", log_f);
    feed_device("/dev/tty1", log_f);
    feed_device("/dev/ttyS0", log_f);
    feed_device("/dev/ttyS1", log_f);
    feed_device("/dev/ttyprintk", log_f);
    feed_device("/dev/vtcon0", log_f);
    feed_device("/dev/fbcon", log_f);*/

    /*fprintf(log_f, "starting shell\n");

    fclose(log_f);

    int fd = open("/var/log/sh_log", O_CREAT | O_WRONLY);*/
/*
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    execve("/bin/sh", NULL, NULL);
*/
    // TODO: run /sbin/init and redirect output to log file

    //close(log_fd);

    return 0;
}