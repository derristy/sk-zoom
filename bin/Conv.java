import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.Closeable;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;

/**
 * Конвертер конфигов Tudey между бинарным форматом игры и XML.
 *
 * Классы импортёра и экспортёра в jar не обфусцированы, а вот методы чтения и
 * записи - да, поэтому они ищутся по сигнатуре: у импортёра это единственный
 * публичный метод без аргументов, возвращающий Object, у экспортёра -
 * единственный публичный void с одним аргументом Object. Известные имена
 * (qd и bg) используются только как подсказка, если кандидатов несколько.
 */
public class Conv
{
    public static void main (String[] args)
        throws Exception
    {
        String mode = args[0], src = args[1], dst = args[2];
        boolean toXML = mode.equals("b2x");

        Object obj;
        InputStream in = new BufferedInputStream(new FileInputStream(src));
        try {
            Object importer = construct(
                toXML ? "com.threerings.export.BinaryImporter" : "com.threerings.export.XMLImporter",
                InputStream.class, in);
            obj = readMethod(importer.getClass()).invoke(importer);
            ((Closeable)importer).close();
        } finally {
            in.close();
        }

        OutputStream out = new BufferedOutputStream(new FileOutputStream(dst));
        try {
            Object exporter = construct(
                toXML ? "com.threerings.export.XMLExporter" : "com.threerings.export.BinaryExporter",
                OutputStream.class, out);
            writeMethod(exporter.getClass()).invoke(exporter, obj);
            ((Closeable)exporter).close();
        } finally {
            out.close();
        }

        System.out.println(obj.getClass().getSimpleName() + ", entries=" +
            (obj.getClass().isArray() ? Array.getLength(obj) : -1));
    }

    /** Создаёт импортёр или экспортёр по единственному потоковому конструктору. */
    protected static Object construct (String className, Class<?> argType, Object arg)
        throws Exception
    {
        Constructor<?> ctor = Class.forName(className).getConstructor(argType);
        return ctor.newInstance(arg);
    }

    /** Метод чтения: public Object <имя>(). */
    protected static Method readMethod (Class<?> clazz)
    {
        List<Method> found = new ArrayList<Method>();
        for (Method m : clazz.getMethods()) {
            if (!Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 0 &&
                    m.getReturnType() == Object.class && m.getDeclaringClass() != Object.class) {
                found.add(m);
            }
        }
        return pick(found, "qd", clazz, "чтения");
    }

    /** Метод записи: public void <имя>(Object). */
    protected static Method writeMethod (Class<?> clazz)
    {
        List<Method> found = new ArrayList<Method>();
        for (Method m : clazz.getMethods()) {
            if (!Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 1 &&
                    m.getParameterTypes()[0] == Object.class && m.getReturnType() == void.class) {
                found.add(m);
            }
        }
        return pick(found, "bg", clazz, "записи");
    }

    protected static Method pick (List<Method> found, String hint, Class<?> clazz, String what)
    {
        if (found.size() == 1) {
            return found.get(0);
        }
        for (Method m : found) {
            if (m.getName().equals(hint)) {
                return m;
            }
        }
        throw new IllegalStateException("в " + clazz.getName() + " не опознан метод " + what +
            ", кандидатов: " + found);
    }
}
